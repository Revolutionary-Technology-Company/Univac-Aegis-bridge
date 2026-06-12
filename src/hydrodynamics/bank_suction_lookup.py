# File Name: bank_suction_lookup.py
# Location: Place this file in your bridge control source tree under '/src/hydrodynamics/'

import numpy as np
from typing import Dict, Any, Tuple

class BankSuctionBoundaryLayerEngine:
    def __init__(self, vessel_length: float, beam: float, draft: float):
        """
        Initializes the dynamic bank interaction lookup engine (Features 26-27).
        vessel_length: Total length of the ship hull (m)
        beam: Total breadth/width of the vessel hull (m)
        draft: Current structural operating draft (m)
        """
        self.L = vessel_length
        self.B = beam
        self.T = draft
        self.rho = 1025.0  # Density of seawater (kg/m^3)
        
        # --- 2D LOOKUP TABLES FOR HYDRODYNAMIC BOUNDARY COEFFICIENTS ---
        # Matrix Axes Definitions:
        # X-Axis: Depth-to-Draft Ratio (h/T) -> Ranging from 1.1 (very shallow) to 4.0 (deep water boundary)
        # Y-Axis: Non-dimensional Wall Distance (y_bank / Beam) -> 0.5 (scraping wall) to 5.0 (wide channel)
        self.depth_to_draft_axis = np.array([1.1, 1.3, 1.5, 2.0, 3.0, 4.0])
        self.distance_to_beam_axis = np.array([0.5, 0.75, 1.0, 1.5, 2.0, 3.5, 5.0])
        
        # Base Empirical Hydrodynamic Lift Coefficients Matrix for Bank Suction (C_Y)
        # Columns correspond to depth ratios, rows correspond to distance ratios
        self.cy_lookup_matrix = np.array([
            [0.180, 0.145, 0.110, 0.075, 0.040, 0.020], # 0.5 beam away (Extreme Force)
            [0.125, 0.098, 0.075, 0.050, 0.025, 0.012], # 0.75 beam away
            [0.085, 0.065, 0.050, 0.032, 0.015, 0.008], # 1.0 beam away
            [0.040, 0.032, 0.024, 0.015, 0.007, 0.003], # 1.5 beam away
            [0.018, 0.014, 0.010, 0.006, 0.002, 0.001], # 2.0 beam away
            [0.004, 0.003, 0.002, 0.001, 0.000, 0.000], # 3.5 beam away
            [0.000, 0.000, 0.000, 0.000, 0.000, 0.000]  # 5.0 beam away (Negligible effect)
        ])
        
        # Base Empirical Turning Moment Coefficients Matrix for Bank Cushion (C_N)
        self.cn_lookup_matrix = np.array([
            [0.045, 0.038, 0.030, 0.020, 0.010, 0.005],
            [0.032, 0.026, 0.020, 0.014, 0.007, 0.003],
            [0.022, 0.018, 0.014, 0.009, 0.004, 0.002],
            [0.010, 0.008, 0.006, 0.004, 0.002, 0.001],
            [0.005, 0.004, 0.003, 0.002, 0.001, 0.000],
            [0.001, 0.001, 0.000, 0.000, 0.000, 0.000],
            [0.000, 0.000, 0.000, 0.000, 0.000, 0.000]
        ])

    def _bilinear_interpolate(self, depth_ratio: float, distance_ratio: float, matrix: np.ndarray) -> float:
        """Helper matrix function performing hard-deterministic 2D bilinear estimation bounds."""
        # Clamp inputs within tracking boundaries to prevent matrix out-of-bounds
        d_ratio = max(self.depth_to_draft_axis[0], min(self.depth_to_draft_axis[-1], depth_ratio))
        dist_ratio = max(self.distance_to_beam_axis[0], min(self.distance_to_beam_axis[-1], distance_ratio))
        
        # Find indices corresponding to bounding bounds
        x_idx = np.searchsorted(self.depth_to_draft_axis, d_ratio) - 1
        y_idx = np.searchsorted(self.distance_to_beam_axis, dist_ratio) - 1
        
        x_idx = max(0, min(x_idx, len(self.depth_to_draft_axis) - 2))
        y_idx = max(0, min(y_idx, len(self.distance_to_beam_axis) - 2))
        
        # Extract bounding intervals
        x0, x1 = self.depth_to_draft_axis[x_idx], self.depth_to_draft_axis[x_idx + 1]
        y0, y1 = self.distance_to_beam_axis[y_idx], self.distance_to_beam_axis[y_idx + 1]
        
        # Get corner coordinates data values
        q00 = matrix[y_idx, x_idx]
        q10 = matrix[y_idx, x_idx + 1]
        q01 = matrix[y_idx + 1, x_idx]
        q11 = matrix[y_idx + 1, x_idx + 1]
        
        # Calculate standard bilinear interpolation weights
        wa = (x1 - d_ratio) * (y1 - dist_ratio)
        wb = (d_ratio - x0) * (y1 - dist_ratio)
        wc = (x1 - d_ratio) * (dist_ratio - y0)
        wd = (d_ratio - x0) * (dist_ratio - y0)
        
        denom = (x1 - x0) * (y1 - y0)
        return (wa * q00 + wb * q10 + wc * q01 + wd * q11) / denom

    def process_bank_forces(self, telemetry: dict) -> dict:
        """
        Executes real-time calculations for Features 26 and 27.
        Returns total forces along with updated safety constraints for the autopilot.
        """
        speed_ms = telemetry['speed_ms']
        water_depth = telemetry['depth']
        distance_to_wall = telemetry['distance_to_bank_meters']
        bank_side = telemetry.get('bank_lateral_side', 'starboard') # 'port' or 'starboard'
        
        # 1. Compute non-dimensional matrix entry parameters
        depth_ratio = water_depth / self.T
        distance_ratio = distance_to_wall / self.B
        
        # 2. Extract interpolated lift and torque coefficients
        c_y = self._bilinear_interpolate(depth_ratio, distance_ratio, self.cy_lookup_matrix)
        c_n = self._bilinear_interpolate(depth_ratio, distance_ratio, self.cn_lookup_matrix)
        
        # 3. FEATURE 26: Bank Suction Force Calculation
        # Y_bank = 0.5 * C_Y * rho * V^2 * L * T
        dynamic_pressure_profile = 0.5 * self.rho * (speed_ms ** 2)
        vessel_profile_area = self.L * self.T
        
        suction_force_newtons = c_y * dynamic_pressure_profile * vessel_profile_area
        
        # 4. FEATURE 27: Bank Cushion Moment Calculation
        # N_bank = 0.5 * C_N * rho * V^2 * L^2 * T
        cushion_moment_nm = c_n * dynamic_pressure_profile * (self.L ** 2) * self.T
        
        # Directional mapping logic based on location orientation offsets
        # If bank is on the starboard side: Suction pulls hull right (+Y), Cushion pushes bow left (-Yaw)
        if bank_side == 'starboard':
            final_suction_force = suction_force_newtons
            final_cushion_moment = -cushion_moment_nm
            suggested_counter_rudder = -math.degrees((cushion_moment_nm) / (dynamic_pressure_profile * vessel_profile_area * 0.5))
        else:
            final_suction_force = -suction_force_newtons
            final_cushion_moment = cushion_moment_nm
            suggested_counter_rudder = math.degrees((cushion_moment_nm) / (dynamic_pressure_profile * vessel_profile_area * 0.5))

        # 5. AUTOPILOT SAFETY CHECK CRITERIA
        # As bank constraints multiply, compress the autopilot's allowed window 
        # to execute normal track modifications without tripping safety overrules.
        severity_index = max(0.0, min(1.0, (c_y / 0.15)))
        max_safe_speed_ms = speed_ms
        
        if severity_index > 0.4:
            # Enforce speed restrictions to reduce the quadratic velocity pressure profile
            max_safe_speed_ms = min(speed_ms, math.sqrt((0.4 * suction_force_newtons) / max(1.0, 0.5 * c_y * self.rho * vessel_profile_area)))
            autopilot_override_flag = True
        else:
            autopilot_override_flag = False

        return {
            "feature_26_suction_force_n": round(final_suction_force, 1),
            "feature_27_cushion_moment_nm": round(final_cushion_moment, 1),
            "suggested_autopilot_counter_rudder_deg": round(suggested_counter_rudder, 2),
            "autopilot_safety_metrics": {
                "bank_interaction_severity_index": round(severity_index, 3),
                "speed_saturation_limit_knots": round(max_safe_speed_ms * 1.94384, 1),
                "lockout_aggressive_maneuvers": autopilot_override_flag
            }
        }

# Verification Execution Profile
if __name__ == "__main__":
    # Setup ship: 45m Length, 9.5m Beam, 3.2m Draft
    engine = BankSuctionBoundaryLayerEngine(vessel_length=45.0, beam=9.5, draft=3.2)
    
    # Mission Scenario: Vessel is traveling at 12 knots (6.17 m/s) down a channel.
    # Telemetry registers the starboard wall has closed in to only 7.2 meters away (less than 1 beam).
    # Water depth has dropped down to 4.16 meters (shallow water scenario, depth ratio ~1.3).
    mock_telemetry = {
        'speed_ms': 6.17,
        'depth': 4.16,
        'distance_to_bank_meters': 7.2,
        'bank_lateral_side': 'starboard'
    }
    
    output = engine.process_bank_forces(mock_telemetry)
    
    print("UNIVAC BANK BOUNDARY LAYER PROTECTION METRICS:\n")
    print(f"Calculated Stern Suction Force: {output['feature_26_suction_force_n']} Newtons (Pulls toward wall)")
    print(f"Calculated Bow Cushion Moment:  {output['feature_27_cushion_moment_nm']} Nm (Pushes bow away)")
    print(f"Preemptive Autopilot Trim Bias: {output['suggested_autopilot_counter_rudder_deg']} Degrees")
    print("\nAUTOPILOT CLOSED LOOP SAFETY PROFILE INTERLOCK DATA:")
    print(output['autopilot_safety_metrics'])
