import math
import numpy as np
import scipy.linalg as la

class HydroCoordinatedPredictor:
    def __init__(self, diameter: float, inertia: float, draft: float, max_torque: float, max_rudder_deg: float, kt: float):
        # Physical Characteristics
        self.D = diameter
        self.J = inertia
        self.draft = draft
        self.max_torque = max_torque
        self.max_rudder_deg = max_rudder_deg
        self.rho = 1025.0
        self.Kt = kt
        
        # Scaling Parameters
        self.alpha = 1.8
        self.beta = 0.6
        self.gamma = 0.015
        
        # PID S-Curve Defaults
        self.max_rpm = 1200.0
        self.max_jerk = 5.0
        self.max_accel = 50.0
        self.current_accel = 0.0
        
        # LQR Weights
        self.Q_lqr = np.diag([15.0, 1.0, 5.0])
        self.R_lqr = np.array([[0.002]])
        
        # EKF States
        self.x_ekf = np.array([[50.0], [3.5]])
        self.P_ekf = np.diag([1.0, 5.0])
        self.Q_ekf = np.diag([0.01, 0.1])
        self.R_ekf = np.array([[0.05]])
        
    # --- 1. Shallow Water & Structural Protection Constraints ---
    def _predict_safe_limits(self, depth: float, current_rpm: float) -> dict:
        omega = (current_rpm * 2.0 * math.pi) / 60.0
        clearance = max(0.2, depth - self.draft)
        clearance_ratio = clearance / self.draft
        
        omega_max_allowed = 125.0 * math.tanh(self.alpha * clearance_ratio)
        rpm_max_allowed = (omega_max_allowed * 60.0) / (2 * math.pi)
        
        rudder_max_allowed = self.max_rudder_deg * math.exp(-self.gamma * abs(omega))
        rudder_slew_rate_max = 15.0 * math.tanh(clearance_ratio)
        
        return {
            'max_safe_rpm': max(20.0, rpm_max_allowed),
            'max_safe_rudder_deg': max(5.0, rudder_max_allowed),
            'max_rudder_slew_rate': max(2.0, rudder_slew_rate_max),
            'clearance_factor': 1.0 + self.beta * (self.draft / clearance)
        }

    # --- 2. Extended Kalman Filter (EKF) for Advance Velocity ---
    def _ekf_estimate_va(self, motor_amps: float, measured_omega: float, dt: float) -> float:
        motor_torque = motor_amps * self.Kt
        omega_hat, va_hat = self.x_ekf[0, 0], self.x_ekf[1, 0]
        
        n = omega_hat / (2 * np.pi)
        J_coeff = va_hat / (n * self.D) if abs(n) >= 0.01 else 0.0
        kq = max(0.005, 0.05 - 0.04 * J_coeff)
        hydro_torque = kq * self.rho * (n**2) * (self.D**5) if abs(n) >= 0.01 else 0.0
        
        d_omega = (motor_torque - hydro_torque) / self.J
        d_va = (4.0 - va_hat) / 2.0
        
        self.x_ekf[0, 0] += d_omega * dt
        self.x_ekf[1, 0] += d_va * dt
        
        dq_domega = 2.0 * 0.035 * self.rho * (omega_hat / (4 * (np.pi**2))) * (self.D**5)
        dq_dva = -0.04 * (1.0 / (n * self.D)) * self.rho * (n**2) * (self.D**5) if n != 0 else 0
        Fc = np.array([[-dq_domega / self.J, -dq_dva / self.J], [0.0, -0.5]])
        Fd = np.eye(2) + Fc * dt
        
        self.P_ekf = np.dot(Fd, np.dot(self.P_ekf, Fd.T)) + self.Q_ekf
        
        H = np.array([[1.0, 0.0]])
        innovation = measured_omega - self.x_ekf[0, 0]
        S = np.dot(H, np.dot(self.P_ekf, H.T)) + self.R_ekf
        K = np.dot(self.P_ekf, np.dot(H.T, np.linalg.inv(S)))
        
        self.x_ekf += K * innovation
        self.P_ekf = np.dot(np.eye(2) - np.dot(K, H), self.P_ekf)
        
        return self.x_ekf[1, 0]

    # --- 3. Coordinated Execution Step ---
    def execute_maneuver(self, target_rpm: float, target_rudder: float, 
                         telemetry: dict, dt: float) -> tuple:
        """ Takes live telemetry (rpm, depth, amps, rudder_deg) and outputs safe mechanical constraints """
        current_rpm = telemetry['rpm']
        current_rudder = telemetry['rudder_deg']
        depth = telemetry['depth']
        amps = telemetry['amps']
        current_omega = (current_rpm * 2.0 * math.pi) / 60.0
        
        limits = self._predict_safe_limits(depth, current_rpm)
        estimated_va = self._ekf_estimate_va(amps, current_omega, dt)
        
        # S-Curve Profiling & Shallow Water Capping
        safe_target_rpm = min(target_rpm, limits['max_safe_rpm'])
        error = safe_target_rpm - current_rpm
        if abs(error) >= 0.1:
            self.current_accel += (1.0 if error > 0 else -1.0) * self.max_jerk * dt
            self.current_accel = max(-self.max_accel, min(self.max_accel, self.current_accel))
        else:
            self.current_accel = 0.0
            
        profiled_target_omega = ((current_rpm + self.current_accel * dt) * 2.0 * math.pi) / 60.0

        # Torque Shedding Logic
        torque_error = 180.0 * (profiled_target_omega - current_omega)
        torque_shed = 450.0 * abs(current_rudder) * (current_omega ** 1.5) * limits['clearance_factor']
        demanded_torque = torque_error - torque_shed
        final_torque = max(-self.max_torque, min(self.max_torque, demanded_torque))
        
        # Rudder Slew Regulation
        safe_target_rudder = max(-limits['max_safe_rudder_deg'], min(limits['max_safe_rudder_deg'], target_rudder))
        rudder_error = safe_target_rudder - current_rudder
        max_move = limits['max_rudder_slew_rate'] * dt
        final_rudder_pos = current_rudder + max(-max_move, min(max_move, rudder_error))
        
        return final_torque, final_rudder_pos, estimated_va
