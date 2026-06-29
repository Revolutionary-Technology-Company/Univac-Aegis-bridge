#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Living Quarters & Utility Control System
Regulates shower valves, pressure ejector cycles, and ventilation arrays.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("LivingQuartersController")

class LivingQuartersController:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        # Physical capacity thresholds
        self.max_greywater_volume_liters = 500.0
        self.current_greywater_level = 22.0
        
        # Operational variables
        self.shower_valves_open = False
        self.exhaust_dampers_open = True
        self.pneumatic_ejector_active = False

    def evaluate_utility_states(self, relay_flags: Dict[str, bool], dt: float) -> Dict[str, Any]:
        """
        Calculates hydraulic and mechanical state tracking loops for the living modules.
        Bypasses standard delivery routes if structural thresholds drop or overflow limits trip.
        """
        # 1. Shower Delivery Logic
        # Bit mapping check to determine if the local module showers are drawing water
        if relay_flags.get("water_heater_active", False) and not self.pneumatic_ejector_active:
            self.shower_valves_open = True
            # Showers introduce fluid velocity into the holding matrices at ~15L per min
            self.current_greywater_level += (0.25 * dt)
        else:
            self.shower_valves_open = False

        # 2. Sump & Greywater Ejector Loop
        # If water volume exceeds safety thresholds, trip automated evacuation pumps
        if self.current_greywater_level >= (self.max_greywater_volume_liters * 0.75):
            self.pneumatic_ejector_active = True
            self.shower_valves_open = False # Fail-safe isolation check: cut supply lines during purge
            logger.critical(f"⚠️ [{self.zone_id}] Greywater high limit reached. Engaging pneumatic ejectors.")
            
        if self.pneumatic_ejector_active:
            # High-velocity decompression drains the tanks rapidly
            self.current_greywater_level = max(10.0, self.current_greywater_level - (2.5 * dt))
            if self.current_greywater_level <= 15.0:
                self.pneumatic_ejector_active = False
                logger.info(f"[{self.zone_id}] Sump system normalization complete. Resetting ejector relays.")

        # 3. Ambient Exhaust Modulation
        # Mirror physical blast door locks to ensure continuous ventilation during seal trends
        if relay_flags.get("blast_door_secured", False):
            self.exhaust_dampers_open = False # Isolate environment from external vectors
        else:
            self.exhaust_dampers_open = True

        return {
            "zone": self.zone_id,
            "shower_valves_energized": self.shower_valves_open,
            "pneumatic_ejector_running": self.pneumatic_ejector_active,
            "ventilation_dampers_sealed": not self.exhaust_dampers_open,
            "holding_tank_utilization_pct": float(self.current_greywater_level / self.max_greywater_volume_liters) * 100.0
        }
