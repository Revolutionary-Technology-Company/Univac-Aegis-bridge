#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Living Quarters & Utility Control System
Regulates shower valves, pressure ejector cycles, and ventilation arrays.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("LivingQuartersController")
logger = logging.getLogger("AcceleratedDrainage")

class AcceleratedLivingQuartersController:
    def __init__(self, zone_id: str, default_capacity_liters: float = 2000.0):
        self.zone_id = zone_id
        
        # Hydraulic Parameters
        self.max_greywater_volume_liters = default_capacity_liters
        self.current_greywater_level = 0.0
        
        # Baseline gravity/pump drain velocity (Liters per second)
        self.PRIMARY_DRAIN_VELOCITY = 1.5 
        # Secondary pneumatic injector acceleration speed (Liters per second)
        self.PNEUMATIC_BOOSTER_VELOCITY = 6.5
        
        # State Indicators
        self.shower_valves_open = False
        self.primary_pump_active = False
        self.pneumatic_booster_active = False
        
        # PID Temperature Variables (Preserved)
        self.current_mix_temperature_c = 20.0
        self.integral_error = 0.0
        self.previous_error = 0.0
        self.Kp, self.Ki, self.Kd = 2.25, 0.35, 0.15

    def evaluate_utility_states(self, relay_flags: Dict[str, bool], target_temp_c: float, dt: float) -> Dict[str, Any]:
        """
        Executes dynamic fluid flow balancing with two-stage high-speed drainage.
        """
        if dt <= 0.0:
            dt = 0.001

        # 1. Calculate Incoming Volume Load (Showers running at full tilt)
        incoming_flow_rate = 0.0
        if relay_flags.get("water_heater_active", False):
            self.shower_valves_open = True
            incoming_flow_rate = 4.5  # High load displacement influx (L/s)
        else:
            self.shower_valves_open = False

        # 2. Sequential Drainage Control Loop
        # Stage 1 Trigger: Normal high-water limit (50% capacity) -> Start baseline pumping
        if self.current_greywater_level >= (self.max_greywater_volume_liters * 0.50):
            self.primary_pump_active = True
        
        # Stage 2 Trigger: CRITICAL ACCELERATION LINE (80% capacity and rising)
        # If inflow continues outstripping primary pump bounds, deploy air pressure injectors
        if self.current_greywater_level >= (self.max_greywater_volume_liters * 0.80):
            if not self.pneumatic_booster_active:
                logger.critical(f"⚠️ [{self.zone_id}] DRAIN LEVEL CRITICAL ({self.current_greywater_level:.1f}L). DEPLOYING DUAL-STAGE PNEUMATIC AUXILIARY BOOST ACCELERATORS.")
            self.pneumatic_booster_active = True
            self.shower_valves_open = False  # Automated protection: Isolate water supply completely

        # Calculate Net Fluid Vector Shift
        outbound_flow_rate = 0.0
        if self.primary_pump_active:
            outbound_flow_rate += self.PRIMARY_DRAIN_VELOCITY
        if self.pneumatic_booster_active:
            outbound_flow_rate += self.PNEUMATIC_BOOSTER_VELOCITY

        # Apply continuous-time Euler integration pass
        net_flow_delta = incoming_flow_rate - outbound_flow_rate
        self.current_greywater_level = max(0.0, min(self.max_greywater_volume_liters, self.current_greywater_level + (net_flow_delta * dt)))

        # Hysteresis Reset points to stop the pumps once the well clears
        if self.current_greywater_level <= (self.max_greywater_volume_liters * 0.10):
            self.primary_pump_active = False
            if self.pneumatic_booster_active:
                logger.info(f"✅ [{self.zone_id}] Well pressure cleared. Safely venting pneumatic booster valves.")
            self.pneumatic_booster_active = False

        # 3. Thermal Modulation Pass (Preserved structural PID logic)
        hot_valve_pct = 0.0
        if self.shower_valves_open:
            error = target_temp_c - self.current_mix_temperature_c
            p_term = self.Kp * error
            self.integral_error = max(-50.0, min(50.0, self.integral_error + (error * dt)))
            i_term = self.Ki * self.integral_error
            d_term = self.Kd * ((error - self.previous_error) / dt)
            self.previous_error = error
            hot_valve_pct = max(0.0, min(100.0, p_term + i_term + d_term))
            self.current_mix_temperature_c += ( ((hot_valve_pct / 100.0) * 60.0 + (1.0 - (hot_valve_pct / 100.0)) * 12.0) - self.current_mix_temperature_c ) * 0.4 * dt
        else:
            self.current_mix_temperature_c += (18.0 - self.current_mix_temperature_c) * 0.1 * dt
            self.integral_error = 0.0

        return {
            "zone": self.zone_id,
            "well_fill_volume_liters": float(round(self.current_greywater_level, 2)),
            "well_load_percentage": (self.current_greywater_level / self.max_greywater_volume_liters) * 100.0,
            "primary_pump_relay": self.primary_pump_active,
            "pneumatic_booster_relay": self.pneumatic_booster_active,
            "showers_disabled_by_overflow": not self.shower_valves_open and relay_flags.get("water_heater_active", False)
        }

class AdvancedLivingQuartersController:
    def __init__(self, zone_id: str, default_capacity_liters: float = 500.0):
        self.zone_id = zone_id
        
        # 1. Dynamic Tank Capacity Thresholds (Physical Well Layout)
        self.max_greywater_volume_liters = default_capacity_liters
        self.current_greywater_level = 0.0
        
        # 2. PID Temperature Regulation Variables
        self.current_mix_temperature_c = 20.0  # Ambient start
        self.integral_error = 0.0
        self.previous_error = 0.0
        
        # Standard industrial PID gains for mixing valves to limit hunting/overshoot
        self.Kp = 2.25
        self.Ki = 0.35
        self.Kd = 0.15
        
        # State tracking flags
        self.shower_valves_open = False
        self.pneumatic_ejector_active = False

    def dynamically_adjust_well_capacity(self, height_meters: float, radius_meters: float) -> float:
        """
        Calculates and updates max tank thresholds using physical layout geometries.
        Formula: V = pi * r^2 * h * 1000 (to convert cubic meters to liters)
        """
        volume_cubic_meters = math.pi * (radius_meters ** 2) * height_meters
        self.max_greywater_volume_liters = volume_cubic_meters * 1000.0
        logger.info(f"[{self.zone_id}] Well topology recalibrated. Max capacity updated to: {self.max_greywater_volume_liters:.2f} Liters.")
        return self.max_greywater_volume_liters

    def compute_valve_pid_modulation(self, target_temp_c: float, current_temp_c: float, dt: float) -> float:
        """
        Executes a discrete time-slice PID calculation for the modulating mix valve.
        Returns hot-water valve percentage opening command string [0.0 to 100.0%].
        """
        if dt <= 0.0:
            return 0.0
            
        error = target_temp_c - current_temp_c
        
        # Proportional term
        p_term = self.Kp * error
        
        # Integral term with windup protection (limit accumulation if valve is fully open/closed)
        self.integral_error += error * dt
        self.integral_error = max(-50.0, min(50.0, self.integral_error))
        i_term = self.Ki * self.integral_error
        
        # Derivative term tracking rapid thermal changes
        d_term = self.Kd * ((error - self.previous_error) / dt)
        self.previous_error = error
        
        # Total output command
        valve_output = p_term + i_term + d_term
        
        # Clamp output bounded to exact physical actuator stops [0% (Full Cold) to 100% (Full Hot)]
        return max(0.0, min(100.0, valve_output))

    def evaluate_utility_states(self, relay_flags: Dict[str, bool], target_temp_c: float, dt: float) -> Dict[str, Any]:
        """
        Executes structural fluid mechanics and thermal regulation passes for the zone.
        """
        # 1. Hydraulic Level Management
        if relay_flags.get("water_heater_active", False) and not self.pneumatic_ejector_active:
            self.shower_valves_open = True
            self.current_greywater_level += (0.35 * dt)  # Continuous inflow scale
        else:
            self.shower_valves_open = False

        # 2. Emergency Overflow Purge Tripping
        if self.current_greywater_level >= (self.max_greywater_volume_liters * 0.80):
            self.pneumatic_ejector_active = True
            self.shower_valves_open = False  # Hard fail-safe isolation
            
        if self.pneumatic_ejector_active:
            self.current_greywater_level = max(0.0, self.current_greywater_level - (3.0 * dt))
            if self.current_greywater_level <= (self.max_greywater_volume_liters * 0.10):
                self.pneumatic_ejector_active = False

        # 3. Modulating Thermal Regulation Step
        hot_valve_pct = 0.0
        if self.shower_valves_open:
            hot_valve_pct = self.compute_valve_pid_modulation(target_temp_c, self.current_mix_temperature_c, dt)
            # Simulated thermodynamic response feedback loop step
            thermal_influence = (hot_valve_pct / 100.0) * 60.0 + (1.0 - (hot_valve_pct / 100.0)) * 12.0
            self.current_mix_temperature_c += (thermal_influence - self.current_mix_temperature_c) * 0.4 * dt
        else:
            # Cool down toward ambient when stagnant
            self.current_mix_temperature_c += (18.0 - self.current_mix_temperature_c) * 0.1 * dt
            self.integral_error = 0.0  # Reset integral cache to eliminate windup artifacts

        return {
            "zone": self.zone_id,
            "shower_active": self.shower_valves_open,
            "well_fill_percentage": (self.current_greywater_level / self.max_greywater_volume_liters) * 100.0,
            "pneumatic_purge_running": self.pneumatic_ejector_active,
            "mix_valve_hot_pct": float(round(hot_valve_pct, 2)),
            "monitored_output_temperature_c": float(round(self.current_mix_temperature_c, 2))
        }

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
