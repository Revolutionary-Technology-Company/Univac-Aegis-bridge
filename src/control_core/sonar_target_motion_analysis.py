# File Name: sonar_target_motion_analysis.py
# Location: /src/sensor_core/

import math

class TargetMotionAnalysis:
    """
    FEATURES 50-59: PASSIVE SONAR TARGET MOTION ANALYSIS (TMA)
    Generates firing solutions purely from acoustic bearing-rate data.
    """
    
    def feature_52_ekelund_ranging(self, own_speed_leg1: float, own_hdg_leg1: float, brg_rate_leg1: float,
                                         own_speed_leg2: float, own_hdg_leg2: float, brg_rate_leg2: float,
                                         mean_target_bearing: float) -> float:
        """
        Calculates range to a target using only passive bearing measurements.
        Requires the hunting ship to make a distinct course/speed change (Leg 1 to Leg 2).
        Speeds in m/s, headings/bearings in radians, bearing rates in rad/s.
        """
        # Calculate the hunting ship's velocity across the line of sight (LOS) for both legs
        v_across_1 = own_speed_leg1 * math.sin(own_hdg_leg1 - mean_target_bearing)
        v_across_2 = own_speed_leg2 * math.sin(own_hdg_leg2 - mean_target_bearing)
        
        # Ekelund Formula: Range = Delta_Velocity_Across_LOS / Delta_Bearing_Rate
        delta_v_across = v_across_2 - v_across_1
        delta_brg_rate = brg_rate_leg2 - brg_rate_leg1
        
        if abs(delta_brg_rate) < 1e-6:
            return -1.0 # Invalid maneuver (Target and Ship are matching courses)
            
        range_estimate_meters = delta_v_across / delta_brg_rate
        return abs(range_estimate_meters)
