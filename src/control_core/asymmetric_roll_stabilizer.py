# File Name: asymmetric_roll_stabilizer.py
# Location: /src/control_core/
# Subsystem: Fire-Synchronized Asymmetric Roll Stabilization Core Plant

import math
import numpy as np
from typing import Dict, Any

class AsymmetricRollStabilizerMatrix:
    def __init__(self, physical_params: dict):
        """
        Initializes the dynamic storm-combat roll stabilizer.
        """
        self.J_roll = float(physical_params['inertia_roll'])
        self.max_actuator = float(physical_params['max_rudder_deg'])
        self.B_beam = float(physical_params['beam'])
        self.L_hull = float(physical_params['hull_length'])
        
        # Actuator allocation gains
        self.Kp_trajectory = 1.6
        self.Kd_nominal_roll = 2.4
        self.K_bias_counter = 3.8
        self.K_fire_lock = 4.5  # Heavy weighting to snap deck plane to weapon axis

        self.roll_history = []
        self.window_size = 50

    def calculate_fire_synchronized_stabilization(self, targets: dict, telemetry: dict, weapon_state: dict, dt: float) -> dict:
        """
        MIMO Asymmetric Loop Core. Stabilizes the hull during storm transits and 
        forces an explicit deck synchronization envelope when firing targets in motion.
        """
        target_yaw_rate = targets.get('target_yaw_rate', 0.0)
        
        current_speed = max(0.1, telemetry.get('speed_ms', 0.0))
        current_yaw_rate = telemetry.get('yaw_rate_rads', 0.0)
        current_roll_rad = telemetry.get('roll_angle_rad', 0.0)
        current_roll_rate = telemetry.get('roll_rate_rads', 0.0)
        
        # 1. Isolate persistent storm-slap listing bias via rolling average window
        self.roll_history.append(current_roll_rad)
        if len(self.roll_history) > self.window_size:
            self.roll_history.pop(0)
        persistent_list_rad = sum(self.roll_history) / len(self.roll_history)

        # 2. Compute Base Steering Trajectory Term (Low-Frequency Heading Maintenance)
        u_steering = self.Kp_trajectory * (target_yaw_rate - current_yaw_rate)

        # 3. Intercept Firing Target Constraints and Wave Synchronization Gating
        fire_engagement_active = weapon_state.get('engagement_sequence_active', False)
        target_elevation_deg = weapon_state.get('target_elevation_deg', 0.0)
        
        # Forward Velocity Vector Lead Correction (Compensates for motion vector during storm slide)
        # Delta_Delta = Forward Speed adjustment factor on rudder lift parameters
        speed_knots = current_speed * 1.94384
        velocity_lead_correction = 0.02 * math.sin(current_yaw_rate) * (speed_knots / 30.0)

        if fire_engagement_active:
            # APEX-LOCK CONFIGURATION: Force deck to match weapon tracking limits
            # If target is high elevation, allow controlled trailing rolling to maximize range parameters
            target_deck_roll_rad = math.radians(max(-8.0, min(8.0, target_elevation_deg * 0.2)))
            
            # Switch to tight tracking loops to freeze hull roll oscillations
            u_roll_control = self.K_fire_lock * (current_roll_rad - target_deck_roll_rad)
            tracking_mode = "APEX_COMBAT_LOCK_ACTIVE"
            
            # Fire command validation gate (Only allow dispatch if roll rate passes near-zero axis)
            ready_to_fire = abs(current_roll_rate) <= 0.03 and abs(current_roll_rad - target_deck_roll_rad) < 0.02
        else:
            # STANDARD STORM DAMPING CONFIGURATION
            u_roll_control = self.K_bias_counter * persistent_list_rad
            tracking_mode = "NOMINAL_STORM_DAMPING"
            ready_to_fire = False

        # 4. Asymmetric Output Matrix Split Generation
        # Scale high-frequency damping quadratically based on fluid speed passing the blades
        dynamic_damping_factor = self.Kd_nominal_roll * ((current_speed ** 2) / 100.0)
        
        delta_port_rad = u_steering + u_roll_control - (dynamic_damping_factor * current_roll_rate) + velocity_lead_correction
        delta_stbd_rad = u_steering - u_roll_control - (dynamic_damping_factor * current_roll_rate) - velocity_lead_correction

        # Convert to system degrees and enforce separate mechanical boundary locks
        port_out = max(-self.max_actuator, min(self.max_actuator, math.degrees(delta_port_rad)))
        stbd_out = max(-self.max_actuator, min(self.max_actuator, math.degrees(delta_stbd_rad)))

        return {
            "command_port_actuator_deg": round(port_out, 2),
            "command_stbd_actuator_deg": round(stbd_out, 2),
            "firing_interlock_cleared": ready_to_fire,
            "stabilization_state": tracking_mode,
            "asymmetric_split_delta_deg": round(abs(port_out - stbd_out), 2),
            "vessel_storm_list_deg": round(math.degrees(persistent_list_rad), 2)
        }

# Verification Execution Profile
if __name__ == "__main__":
    vessel_specs = {'inertia_roll': 850000.0, 'max_rudder_deg': 35.0, 'beam': 9.5, 'hull_length': 45.0}
    stabilizer = AsymmetricRollStabilizerMatrix(vessel_specs)
    
    # Storm Telemetry Simulation: Vessel cruising at 14 knots through Sea State 6 waves.
    # High-speed weapon parser orders a high-elevation engagement track.
    mock_telemetry = {'speed_ms': 7.2, 'yaw_rate_rads': 0.03, 'roll_angle_rad': -0.08, 'roll_rate_rads': 0.01}
    mock_targets = {'target_yaw_rate': 0.03}
    mock_weapon_state = {'engagement_sequence_active': True, 'target_elevation_deg': 35.0}
    
    stabilizer.roll_history = [-0.08] * 30 # Pre-seed storm listing history
    
    output = stabilizer.calculate_fire_synchronized_stabilization(mock_targets, mock_telemetry, mock_weapon_state, dt=0.02)
    print("STORM ENGAGEMENT STABILIZATION LOOP RESULTS:")
    print("-" * 65)
    print(f"Operational Mode:       {output['stabilization_state']}")
    print(f"Port Surface Output:    {output['command_port_actuator_deg']}°")
    print(f"Starboard Surface Out:  {output['command_stbd_actuator_deg']}°")
    print(f"Asymmetric Split Delta: {output['asymmetric_split_delta_deg']}°")
    print(f"FIRING WINDOW PERMIT:   {output['firing_interlock_cleared']} (Weapon Dispatch Authorized)")
