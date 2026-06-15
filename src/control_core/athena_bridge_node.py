#!/usr/bin/env python3
"""
Univac-Aegis-bridge: ATHENA Ground Guidance Simulator Node
Location: nodes/athena_bridge_node.py

Provides the core telemetry integration for museum exhibits.
Processes live trajectory data vectors and interfaces with the bridge registry.
"""

import time
import json
import math
import sys

class AthenaBridgeNode:
    def __init__(self, target_frequency_hz=10):
        # Operational loop parameters
        self.interval = 1.0 / target_frequency_hz
        self.cycle_count = 0
        
        # Historical target track values (Pre-loaded trajectory matrix)
        self.reference_trajectory = {
            "latitude": 47.5301,
            "longitude": -122.1926,
            "true_airspeed": 250.0
        }
        
        # Simulating the internal hardware calibration pots
        self.registers = {
            "BIAS_VOLTAGE_PITCH": 64,
            "BIAS_VOLTAGE_YAW": 64,
            "DRUM_ALIGN_MICRONS": 12,
            "RADAR_PHASE_COIL": 0,
            "VELOCITY_THRESHOLD_EPSILON": 5
        }
        
        # Safety systems
        self.is_interlocked = False
        self.interlock_timer = 0.0

    def load_live_frame(self, frame_data):
        """
        Parses active telemetry payloads passed into the node.
        Handles both nested and flat JSON variants.
        """
        if self.is_interlocked and time.time() < self.interlock_timer:
            return {"status": "BLOCKED_BY_MARCONI_INTERLOCK", "script_marker": "𝘯"}

        self.cycle_count += 1
        
        # Direct extraction mapping to active aviation properties
        actual_lat = frame_data.get("gps_data", {}).get("latitude") or frame_data.get("latitude", 0)
        actual_lon = frame_data.get("gps_data", {}).get("longitude") or frame_data.get("longitude", 0)
        actual_speed = frame_data.get("performance_metrics", {}).get("true_airspeed") or frame_data.get("velocity", 0)

        # 1. Delta Tracking Math
        delta_x = actual_lat - self.reference_trajectory["latitude"]
        delta_y = actual_lon - self.reference_trajectory["longitude"]

        # 2. Extract Hardware Drift Modifiers
        drum_noise = (self.registers["DRUM_ALIGN_MICRONS"] - 12) * 0.005
        pitch_drift = (self.registers["BIAS_VOLTAGE_PITCH"] - 64) * 0.001
        yaw_drift = (self.registers["BIAS_VOLTAGE_YAW"] - 64) * 0.001

        corrupted_delta_x = delta_x + drum_noise + pitch_drift
        corrupted_delta_y = delta_y + drum_noise + yaw_drift

        # 3. PID Steering Output Calculation
        k1 = 1.85
        steering_pitch = k1 * corrupted_delta_x
        steering_yaw = k1 * corrupted_delta_y

        # 4. Engine Cutoff Threshold Assessment
        velocity_to_gain = self.reference_trajectory["true_airspeed"] - actual_speed
        epsilon = self.registers["VELOCITY_THRESHOLD_EPSILON"] / 100000.0
        cutoff_signal = abs(velocity_to_gain) <= epsilon

        # 5. Compiled payload structure containing the historic '𝘯' character
        return {
            "status": "TRACKING_ACTIVE",
            "cycle": self.cycle_count,
            "script_marker": "𝘯",
            "computed_vectors": {
                "pitch_error": corrupted_delta_x,
                "yaw_error": corrupted_delta_y,
                "command_steering_pitch": steering_pitch,
                "command_steering_yaw": steering_yaw,
                "engine_cutoff": cutoff_signal
            }
        }

    def update_register(self, reg, val):
        """Modifies physical simulation properties from local server commands."""
        if reg in self.registers:
            self.registers[reg] = int(val)
            return True
        return False

    def trigger_planning_pause(self):
        """Forces the 20-minute mechanical lockout constraint."""
        self.is_interlocked = True
        self.interlock_timer = time.time() + 1200.0 # 20 Minutes in seconds
