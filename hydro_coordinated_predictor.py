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
        self.L_ship = 150.0 # Length from bow sensor to propeller (meters)
        
        # S-Curve & Environmental Constants
        self.max_jerk = 5.0
        self.max_accel = 50.0
        self.current_accel = 0.0
        self.g = 9.81
        
        # --- LQR State Weights for RRS (Rudder Roll Stabilization) ---
        # States: [sway_vel, yaw_rate, roll_angle, roll_rate]
        self.Q_rrs = np.diag([1.0, 50.0, 100.0, 50.0]) 
        self.R_rrs = np.array([[0.1]]) # Penalize excessive rudder slew
        
        # Mock pre-computed LQR feedback gain matrix for the MIMO system
        # K = [K_sway, K_yaw, K_roll_angle, K_roll_rate]
        self.K_rrs = np.array([0.5, 12.0, -8.5, -4.2]) 

        # EKF States for Advance Velocity
        self.x_ekf = np.array([[50.0], [3.5]])
        self.P_ekf = np.diag([1.0, 5.0])
        self.Q_ekf = np.diag([0.01, 0.1])
        self.R_ekf = np.array([[0.05]])
        
    # --- 1. Wave Dispersion Prediction (Anticipating the Crest) ---
    def predict_wave_impact(self, wave_freq_hz: float, vessel_speed_ms: float, heading_rad: float) -> float:
        """
        Calculates the hydrodynamic dispersion relation to predict when a wave 
        measured at the bow will strike the propeller at the stern.
        """
        if wave_freq_hz <= 0.01:
            return 0.0 # Flat water
            
        omega_w = 2.0 * math.pi * wave_freq_hz
        k_wave = (omega_w ** 2) / self.g
        c_p = self.g / omega_w # Phase velocity
        
        # Time delay for wave to travel from bow sensor to stern
        # dt = L / (c_p + V * cos(mu))
        relative_velocity = c_p + (vessel_speed_ms * math.cos(heading_rad))
        t_delay = self.L_ship / max(0.1, relative_velocity)
        
        return t_delay

    # --- 2. Propeller Ventilation & Torque Shedding ---
    def calculate_wave_torque_limit(self, current_rpm: float, wave_amplitude: float, wave_phase: float) -> tuple:
        """
        Reduces motor torque preemptively if the stern pitches up, 
        preventing the propeller from overspeeding in thin water.
        """
        n = current_rpm / 60.0
        if n == 0: return 0.0, 1.0
        
        # Calculate dynamic depth of the propeller shaft
        dynamic_depth = self.draft + (wave_amplitude * math.sin(wave_phase))
        submergence_ratio = max(0.0, dynamic_depth / self.D)
        
        # Ventilation factor (Beta): 1.0 = fully submerged, 0.0 = completely out of water
        beta = min(1.0, math.tanh(1.5 * submergence_ratio))
        
        # Calculate standard hydrodynamic load torque, scaled by the ventilation factor
        kq = 0.04 # Simplified torque coefficient
        q_h = kq * self.rho * (n**2) * (self.D**5)
        q_h_actual = q_h * beta
        
        return q_h_actual, beta

    # --- 3. Rudder Roll Stabilization (MIMO Matrix Calculation) ---
    def calculate_rrs_command(self, target_yaw_rate: float, current_yaw_rate: float, 
                              roll_angle_rad: float, roll_rate_rads: float) -> float:
        """
        Calculates the high-frequency rudder twitch required to cancel roll energy
        without disrupting the low-frequency turn trajectory.
        """
        yaw_error = target_yaw_rate - current_yaw_rate
        
        # Apply LQR feedback gains:
        # We want yaw_error to reach 0, and roll states to remain 0.
        rudder_steer = self.K_rrs[1] * yaw_error
        rudder_stabilize = (self.K_rrs[2] * roll_angle_rad) + (self.K_rrs[3] * roll_rate_rads)
        
        # Cross-coupled command
        raw_rudder_cmd_rad = rudder_steer + rudder_stabilize
        return math.degrees(raw_rudder_cmd_rad)

    # --- 4. Main Coordinated Execution Step ---
    def execute_maneuver(self, target_rpm: float, target_yaw_rate: float, 
                         telemetry: dict, dt: float) -> tuple:
        """ 
        Ingests real-time Aegis commands and hull telemetry.
        Outputs physically safe, roll-stabilized torque and rudder angles.
        """
        # Unpack Telemetry
        current_rpm = telemetry['rpm']
        depth = telemetry['depth']
        amps = telemetry['amps']
        vessel_speed_ms = telemetry['speed_ms']
        wave_amp = telemetry.get('wave_amp_m', 0.0)
        wave_freq = telemetry.get('wave_freq_hz', 0.1)
        wave_phase = telemetry.get('wave_phase_rad', 0.0)
        roll_angle = telemetry.get('roll_rad', 0.0)
        roll_rate = telemetry.get('roll_rate_rads', 0.0)
        yaw_rate = telemetry.get('yaw_rate_rads', 0.0)

        # 1. Wave Dispersion Lookahead
        impact_delay = self.predict_wave_impact(wave_freq, vessel_speed_ms, heading_rad=0.0)
        predicted_phase = wave_phase + (2.0 * math.pi * wave_freq * impact_delay)

        # 2. Torque Shedding & S-Curve Limits
        q_h, beta = self.calculate_wave_torque_limit(current_rpm, wave_amp, predicted_phase)
        
        safe_target_rpm = target_rpm # Would be capped by shallow water math here
        error = safe_target_rpm - current_rpm
        if abs(error) >= 0.1:
            self.current_accel += (1.0 if error > 0 else -1.0) * self.max_jerk * dt
            self.current_accel = max(-self.max_accel, min(self.max_accel, self.current_accel))
        else:
            self.current_accel = 0.0
            
        current_omega = (current_rpm * 2.0 * math.pi) / 60.0
        profiled_target_omega = ((current_rpm + self.current_accel * dt) * 2.0 * math.pi) / 60.0

        # Calculate final torque command, preemptively dropping power if beta < 1.0 (propeller broaching)
        torque_error = 180.0 * (profiled_target_omega - current_omega)
        demanded_torque = torque_error + q_h
        # Scale max allowable torque by ventilation factor to prevent free-spinning
        dynamic_max_torque = self.max_torque * beta 
        final_torque = max(-dynamic_max_torque, min(dynamic_max_torque, demanded_torque))
        
        # 3. Rudder Roll Stabilization (RRS)
        final_rudder_pos = self.calculate_rrs_command(target_yaw_rate, yaw_rate, roll_angle, roll_rate)
        
        # Apply strict hydraulic slew rate limit (15 deg/s max)
        max_move = 15.0 * dt
        current_rudder = telemetry.get('rudder_deg', 0.0)
        clamped_rudder = current_rudder + max(-max_move, min(max_move, final_rudder_pos - current_rudder))
        
        final_rudder_pos = max(-self.max_rudder_deg, min(self.max_rudder_deg, clamped_rudder))
        
        return final_torque, final_rudder_pos, beta
