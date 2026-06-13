# File Name: central_warning_registry.py
# Location: /src/control_core/
# Subsystem: Centralized Warning Interlock and Actuator Override Registry

import math
import time
from typing import Dict, Any, Tuple

class CentralWarningRegistry:
    def __init__(self, physical_bounds: dict):
        """Initializes the multi-variable warning and safety override matrix."""
        self.draft = float(physical_bounds.get('draft', 6.5))
        self.max_torque = float(physical_bounds.get('max_torque', 90000.0))
        self.lock = threading_lock = None # Safe internal standalone tracking definitions
        
        # Internal warning status bit registers
        self.active_warning_mask = 0
        self.fault_messages = []

    def evaluate_physical_warning_gates(self, telemetry: dict, targets: dict) -> Tuple[bool, dict]:
        """
        Evaluates physical warning inputs (Water, Heat, Fire, Attitude, Crash) at 50Hz.
        Returns a boolean indicating if a hard interlock trip requires a torque shutdown.
        """
        force_torque_shutdown = False
        self.fault_messages.clear()
        self.active_warning_mask = 0
        
        # 1. NODE 219: Water Warning (Keel Clearance Check)
        clearance = telemetry.get('depth', 50.0) - self.draft
        if clearance <= 1.0:
            self.active_warning_mask |= (1 << 0)
            self.fault_reports_append = "CRITICAL_WATER_GROUNDING_WARNING"
            force_torque_shutdown = True

        # 2. NODE 221: Heat Warning (Thermal Casing Check)
        core_temp = telemetry.get('computer_temperature_c', 25.0)
        if core_temp >= 85.0:
            self.active_warning_mask |= (1 << 1)
            self.fault_messages.append("CORE_THERMAL_CRITICAL_WARNING")
            # Proactively scale down allowed power variables instead of full shutdown
            targets['rpm'] = min(targets.get('rpm', 500.0), 150.0)

        # 3. NODE 224: Fire Warning (Rapid Thermal Elevation Check)
        magazine_temp = telemetry.get('magazine_temperature_c', 22.0)
        if magazine_temp >= 70.0:
            self.active_warning_mask |= (1 << 2)
            self.fault_messages.append("FIRE_ALARM_MAGAZINE_DELUGE_ACTIVE")
            force_torque_shutdown = True

        # 4. NODE 225: Attitude Warning (Orientation Envelope Check)
        roll_angle_deg = math.degrees(abs(telemetry.get('roll_angle_rad', 0.0)))
        if roll_angle_deg >= 25.0:
            self.active_warning_mask |= (1 << 3)
            self.fault_messages.append("ATTITUDE_ENVELOPE_EXCEEDED_ROLL_CRITICAL")

        # 5. NODE 227: Crash Warning (Imminent Collision Check)
        distance_to_obstacle_m = telemetry.get('distance_to_obstacle_meters', 500.0)
        vessel_speed_ms = telemetry.get('speed_ms', 0.0)
        
        # Calculate time-to-impact if speed is maintained
        time_to_impact = distance_to_obstacle_m / max(0.1, vessel_speed_ms)
        if time_to_impact <= 3.0 and distance_to_obstacle_m < 50.0:
            self.active_warning_mask |= (1 << 4)
            self.fault_messages.append("CRASH_IMMINENT_COLLISION_INTERLOCK_TRIP")
            force_torque_shutdown = True

        report_payload = {
            "warning_bitmask_hex": f"0x{self.active_warning_mask:04X}",
            "active_faults": list(self.fault_messages),
            "safety_shutdown_engaged": force_torque_shutdown,
            "timestamp_resolved": time.time()
        }

        return force_torque_shutdown, report_payload
