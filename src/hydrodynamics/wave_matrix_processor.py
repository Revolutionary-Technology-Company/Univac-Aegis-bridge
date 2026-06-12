# File Name: wave_matrix_processor.py
# Location: Place this file in your bridge control source tree under '/src/hydrodynamics/'

import math
import numpy as np
from typing import Dict, Any, Tuple

class AutoregressiveWaveMatrixProcessor:
    def __init__(self, diameter: float, inertia: float, max_torque: float):
        """
        Initializes the UNIVAC-inspired feature matrix (Features 40-43).
        diameter: Propeller diameter (m)
        inertia: Shaft and propeller combined rotational mass (kg*m^2)
        max_torque: Maximum engine drive torque limitation (Nm)
        """
        self.D = diameter
        self.J = inertia
        self.max_torque = max_torque
        self.g = 9.81
        self.rho = 1025.0 # Seawater density
        
        # --- FEATURE 40: HISTORICAL BUFFER ---
        # 5-Step Memory array tracking forward wave sensor shifts
        self.history_depth = 5
        self.elevation_history = np.zeros(self.history_depth)
        
        # Linear AR prediction weights derived from stochastic oceanographic wave spectra
        self.ar_weights = np.array([0.842, -0.441, 0.198, -0.048, 0.009])
        
        # --- FEATURE 43: NOTCH FILTER STATES ---
        # State registers for the second-order digital notch filter
        self.notch_x1 = 0.0
        self.notch_x2 = 0.0
        self.notch_y1 = 0.0
        self.notch_y2 = 0.0

    def execute_feature_40_ar_filter(self, raw_bow_reading: float) -> float:
        """
        FEATURE 40: Autoregressive Prediction Filter.
        Shifts the temporal history matrix and runs a dot-product forecast 
        to project future water elevation trends at the stern.
        """
        # Shift memory registers left
        self.elevation_history = np.roll(self.elevation_history, -1)
        self.elevation_history[-1] = raw_bow_reading
        
        # Compute forward dot-product forecasting vector
        predicted_elevation_delta = np.dot(self.ar_weights, self.elevation_history)
        return float(predicted_elevation_delta)

    def execute_feature_41_ventilation_profile(self, predicted_stern_elevation: float, nominal_depth: float) -> float:
        """
        FEATURE 41: Propeller Ventilation Condition.
        Maps the instantaneous submergence boundary ratio of the blades.
        Returns beta_v tracking value from 0.05 (severe aeration) to 1.0 (deep water safe).
        """
        absolute_submergence = nominal_depth + predicted_stern_elevation
        
        if absolute_submergence >= self.D:
            return 1.0
        elif absolute_submergence <= 0.0:
            return 0.05  # Propeller fully exposed to air
        else:
            # Hydrodynamic lift reduction scaling via sinusoidal boundary mapping
            return math.sin((math.pi / 2.0) * (absolute_submergence / self.D)) ** 2

    def execute_feature_42_torque_attenuation(self, base_torque: float, beta_v: float) -> float:
        """
        FEATURE 42: Active Torque Attenuation Engine.
        Preemptively clamps driving engine energy down if the aeration risk
        index rises, protecting the shaft matrix from high-speed free-spin shock loads.
        """
        if beta_v < 0.90:
            # Attenuate engine target commands proportionally ahead of boundary breakdown
            attenuated_torque = base_torque * (beta_v ** 2)
        else:
            attenuated_torque = base_torque
            
        return max(-self.max_torque, min(self.max_torque, attenuated_torque))

    def execute_feature_43_notch_filter(self, rudder_command_deg: float, dt: float) -> float:
        """
        FEATURE 43: Adaptive Notch Filter.
        Removes wave encounter frequencies (typically ~0.8 rad/s) from steering vectors 
        to prevent hydraulic thrashing while preserving low-frequency trajectory trends.
        """
        w_wave = 0.82  # Target wave frequency rejection band (rad/s)
        zeta_1 = 0.05  # Deep narrow attenuation notch width
        zeta_2 = 0.70  # Broad tracking passband damping
        
        # Pre-warp bilinear transform coefficient
        tan_coef = math.tan((w_wave * dt) / 2.0)
        
        # Standard discrete transfer function b/a recursive calculation components
        b0 = 1.0 + (2.0 * zeta_1 * tan_coef) + (tan_coef ** 2)
        b1 = 2.0 * (tan_coef ** 2) - 2.0
        b2 = 1.0 - (2.0 * zeta_1 * tan_coef) + (tan_coef ** 2)
        
        a0 = 1.0 + (2.0 * zeta_2 * tan_coef) + (tan_coef ** 2)
        a1 = 2.0 * (tan_coef ** 2) - 2.0
        a2 = 1.0 - (2.0 * zeta_2 * tan_coef) + (tan_coef ** 2)
        
        # Calculate filtered output using Direct Form I difference logic
        filtered_rudder = (b0/a0)*rudder_command_deg + (b1/a0)*self.notch_x1 + (b2/a0)*self.notch_x2 - (a1/a0)*self.notch_y1 - (a2/a0)*self.notch_y2
        
        # Push historical variables deep into state registers
        self.notch_x2 = self.notch_x1
        self.notch_x1 = rudder_command_deg
        self.notch_y2 = self.notch_y1
        self.notch_y1 = filtered_rudder
        
        return filtered_rudder

    def process_wave_matrix(self, input_metrics: dict, dt: float) -> dict:
        """
        Main routing function executing the integrated 40-43 matrix layer.
        Also compiles an outbound API data payload to support external autonomy nodes.
        """
        raw_bow = input_metrics['bow_sensor_meters']
        base_torque_nm = input_metrics['nominal_calculated_torque_nm']
        rudder_in_deg = input_metrics['unfiltered_rudder_deg']
        nominal_shaft_depth = input_metrics.get('nominal_shaft_depth_meters', 4.0)
        
        # Step 1: Feature 40 - Forecast elevation trends
        predicted_elevation = self.execute_feature_40_ar_filter(raw_bow)
        
        # Step 2: Feature 41 - Establish ventilation constraints
        beta_v = self.execute_feature_41_ventilation_profile(predicted_elevation, nominal_shaft_depth)
        
        # Step 3: Feature 42 - Generate safe torque control levels
        safe_torque = self.execute_feature_42_torque_attenuation(base_torque_nm, beta_v)
        
        # Step 4: Feature 43 - Apply adaptive filtering to the steering vector
        safe_rudder = self.execute_feature_43_notch_filter(rudder_in_deg, dt)
        
        # --- CO-PROCESSOR UPSTREAM EXPORT INTERFACE ---
        # Compiles localized water telemetry alerts designed to patch holes in 
        # external autonomy layers (e.g. Sea Machines/Aegis missing rapid sub-surface density shifts)
        co_processor_external_api_payload = {
            "Aegis_SeaMachines_Interlock": {
                "subsurface_aeration_warning": True if beta_v < 0.85 else False,
                "hydrodynamic_efficiency_multiplier": round(beta_v, 3),
                "predicted_stern_swell_meters": round(predicted_elevation, 2),
                "suggested_external_colregs_slew_rate_modifier": round(max(0.2, beta_v), 2),
                "wave_induced_rudder_torque_load_nm": round(abs(safe_rudder - rudder_in_deg) * 3150.0, 1)
            }
        }
        
        return {
            "command_motor_torque_nm": round(safe_torque, 1),
            "command_rudder_angle_deg": round(safe_rudder, 2),
            "internal_ventilation_index": round(beta_v, 3),
            "upstream_autonomy_telemetry": co_processor_external_api_payload
        }

# Verification Execution Profile
if __name__ == "__main__":
    # Standard profile configuration: 3.2m Propeller matrix
    processor = AutoregressiveWaveMatrixProcessor(diameter=3.2, inertia=400.0, max_torque=85000.0)
    dt = 0.1 # 100ms loop standard
    
    # Mission Scenario: Vessel encounters an aggressive wave sequence.
    # The steering engine commands a 15-degree corrective turn, but the raw bow sensor 
    # suddenly drops -2.4 meters into a heavy wave trough.
    mock_runtime_inputs = {
        'bow_sensor_meters': -2.4,
        'nominal_calculated_torque_nm': 65000.0,
        'unfiltered_rudder_deg': 15.0,
        'nominal_shaft_depth_meters': 3.8
    }
    
    output = processor.process_wave_matrix(mock_runtime_inputs, dt)
    
    print("UNIVAC REPLACEMENT CO-PROCESSOR MATRIX ENGINE OUTPUT:\n")
    print(f"Safe Attenuated Motor Torque: {output['command_motor_torque_nm']} Nm")
    print(f"Notch-Filtered Rudder Angle: {output['command_rudder_angle_deg']} Degrees")
    print(f"Propeller Ventilation Modifier: {output['internal_ventilation_index']}")
    print("\nUPSTREAM EXTERNAL TELEMETRY DISPATCH SENT TO AEGIS/SEA MACHINES VIA BUS:")
    print(list(output['upstream_autonomy_telemetry'].values())[0])
