# File Name: anchor_interlock_subroutine.py
# Location: /src/control_core/
# Subsystem: Weapons-Coupled Autonomous Anchor Windlass Interlock

import time
from typing import Dict, Any

class AutonomousAnchorInterlockSubroutine:
    def __init__(self):
        """
        Initializes the anchor windlass protection interlock state plant.
        """
        # Valid States: "RELEASED", "RETRACTING", "LOCKED_EMERGENCY"
        self.anchor_state = "RELEASED"
        self.navy_manual_override_unlocked = True

    def evaluate_anchor_safety_matrix(self, weapon_metrics: dict, user_override_unlock: bool) -> dict:
        """
        Evaluates gun-ring velocities and weapon engagement flags. 
        Forces immediate anchor recovery and mechanical brake locking on wake-up.
        """
        self.navy_manual_override_unlocked = user_override_unlock

        # Extract live weapon bus triggers
        az_rate = abs(weapon_metrics.get('azimuth_rate_rads', 0.0))
        el_rate = abs(weapon_metrics.get('elevation_rate_rads', 0.0))
        firing_active = weapon_metrics.get('bus_sync_active', False) or weapon_metrics.get('engagement_sequence_active', False)

        # Gating Threshold: If gun is tracking faster than 0.02 rad/s or active firing is true
        weapon_is_awake = (az_rate > 0.02) or (el_rate > 0.02) or firing_active

        # --- STATE MACHINE CONTROL MATRIX ---
        if weapon_is_awake:
            # Overrule Sea Machines instantly. Anchor must hoist and lock.
            self.anchor_state = "LOCKED_EMERGENCY"
            command_windlass_clutch = 1  # 1 = Force Heave/Brake Engage
            command_brake_solenoid = 1  # 1 = Mechanical Lock Pin Engaged
            status_msg = "CRITICAL: Weapons Awake. Anchor Interlock Forced LOCKED."
            sea_machines_allowed = False
        else:
            if self.anchor_state == "LOCKED_EMERGENCY":
                if self.navy_manual_override_unlocked:
                    # Only return control to standard transit if Navy explicitly commands release
                    self.anchor_state = "RELEASED"
                    command_windlass_clutch = 0 # 0 = Free drop / Sea Machines standard
                    command_brake_solenoid = 0
                    status_msg = "NOMINAL: Navy Override Active. Anchor released to Sea Machines."
                    sea_machines_allowed = True
                else:
                    # Weapons went quiet but Navy has not yet cleared the safety release code
                    command_windlass_clutch = 1
                    command_brake_solenoid = 1
                    status_msg = "HOLD: Weapons Secure. Awaiting Manual Navy Unlock Command."
                    sea_machines_allowed = False
            else:
                # Nominal default state: Sea Machines completely manages anchoring profiles
                self.anchor_state = "RELEASED"
                command_windlass_clutch = 0
                command_brake_solenoid = 0
                status_msg = "NOMINAL: Sea Machines autonomous anchor loop active."
                sea_machines_allowed = True

        return {
            "anchor_lock_state": self.anchor_state,
            "command_windlass_clutch_engage": command_windlass_clutch,
            "command_brake_solenoid_lock": command_brake_solenoid,
            "sea_machines_anchor_authority_allowed": sea_machines_allowed,
            "telemetry_status_message": status_msg
        }

# Verification Execution Profile
if __name__ == "__main__":
    interlock = AutonomousAnchorInterlockSubroutine()
    
    print("TESTING AUTONOMOUS ANCHOR WEAPON INTERLOCK PLANT:")
    print("=" * 70)
    
    # Scenario 1: Vessel sitting idle. Sea Machines drops anchor. Weapon is asleep.
    mock_weapon_idle = {'azimuth_rate_rads': 0.0, 'elevation_rate_rads': 0.0, 'bus_sync_active': False}
    res_1 = interlock.evaluate_anchor_safety_matrix(mock_weapon_idle, user_override_unlock=False)
    print(f"Scenario 1 -> State: {res_1['anchor_lock_state']} | Msg: {res_1['telemetry_status_message']}")
    
    # Scenario 2: Gun mount suddenly awakens and tracks target coordinates
    mock_weapon_active = {'azimuth_rate_rads': 0.15, 'elevation_rate_rads': 0.05, 'bus_sync_active': True}
    res_2 = interlock.evaluate_anchor_safety_matrix(mock_weapon_active, user_override_unlock=False)
    print(f"Scenario 2 -> State: {res_2['anchor_lock_state']} | Msg: {res_2['telemetry_status_message']}")
    
    # Scenario 3: Gun goes quiet, but navy has not released the lock
    res_3 = interlock.evaluate_anchor_safety_matrix(mock_weapon_idle, user_override_unlock=False)
    print(f"Scenario 3 -> State: {res_3['anchor_lock_state']} | Msg: {res_3['telemetry_status_message']}")
    
    # Scenario 4: Navy issues manual unlock command over TCP bus
    res_4 = interlock.evaluate_anchor_safety_matrix(mock_weapon_idle, user_override_unlock=True)
    print(f"Scenario 4 -> State: {res_4['anchor_lock_state']} | Msg: {res_4['telemetry_status_message']}")
