# File Name: jammer_targeting_system.py
# Location: /src/control_core/
# Subsystem: Asymmetric Radar Jammer Target Estimator and Weapons Allocator

import math
from typing import Dict, Any, List

class RadarJammerTargetingSystem:
    def __init__(self, own_ship_x: float = 0.0, own_ship_y: float = 0.0):
        """
        Initializes the electronic warfare cross-bearing targeting plant.
        Positions are processed in standardized grid coordinate metrics (meters).
        """
        self.x_own = own_ship_x
        self.y_own = own_ship_y
        
        # Internal calculated threat location
        self.computed_jammer_state = {
            'target_x': 0.0,
            'target_y': 0.0,
            'range_meters': 0.0,
            'bearing_true_deg': 0.0,
            'triangulation_valid': False
        }

    def compute_jammer_location(self, own_strobe_deg: float, partner_ship_telemetry: dict) -> dict:
        """
        Performs 2D line intersection triangulation using cross-bearings 
        received off your network link lines to expose the jammer coordinates.
        
        partner_ship_telemetry expects: {'x_m': float, 'y_m': float, 'strobe_deg': float}
        """
        # Convert true bearings into mathematical Cartesian plane angles (radians)
        theta_a = math.radians(90.0 - own_strobe_deg)
        theta_b = math.radians(90.0 - partner_ship_telemetry['strobe_deg'])
        
        xb, yb = partner_ship_telemetry['x_m'], partner_ship_telemetry['y_m']
        xa, ya = self.x_own, self.y_own
        
        # Verify the two strobe lines are not parallel (prevent division by zero errors)
        if abs(math.tan(theta_a) - math.tan(theta_b)) < 0.001:
            self.computed_jammer_state['triangulation_valid'] = False
            return self.computed_jammer_state
            
        try:
            # Line intersection algorithm matrix calculation
            tan_a = math.tan(theta_a)
            tan_b = math.tan(theta_b)
            
            xj = (yb - ya + xa * tan_a - xb * tan_b) / (tan_a - tan_b)
            yj = ya + (xj - xa) * tan_a
            
            # Calculate range and true bearing from your own hull to the target coordinate
            dx = xj - xa
            dy = yj - ya
            range_to_target = math.sqrt(dx**2 + dy**2)
            bearing_rad = math.atan2(dx, dy)
            bearing_deg = (math.degrees(bearing_rad) + 360.0) % 360.0
            
            self.computed_jammer_state = {
                'target_x': xj,
                'target_y': yj,
                'range_meters': range_to_target,
                'bearing_true_deg': bearing_deg,
                'triangulation_valid': True if range_to_target < 150000.0 else False
            }
        except ZeroDivisionError:
            self.computed_jammer_state['triangulation_valid'] = False
            
        return self.computed_jammer_state

    def allocate_idle_weapons(self, available_mounts: List[dict]) -> List[dict]:
        """
        Scans all available shipboard weapons systems. If a mount is not actively
        engaged in secondary mission defense tracking loops, it overrides its targeting
        registers and slaves it straight onto the computed radar jammer coordinate.
        
        available_mounts expects a list of dicts: 
        [{'mount_id': 'MK45_FORWARD', 'is_engaged': bool, 'current_azimuth': float}]
        """
        assigned_mount_commands = []
        
        if not self.computed_jammer_state['triangulation_valid']:
            # No valid targeting coordinates available; bypass resource re-allocation
            return assigned_mount_commands
            
        target_bearing = self.computed_jammer_state['bearing_true_deg']
        
        for mount in available_mounts:
            # Check the hard-deterministic operational engagement status flag
            if not mount['is_engaged']:
                # SYSTEM OVERRIDE: Slave the idle mount to the active threat coordinates
                mount_command = {
                    'mount_id': mount['mount_id'],
                    'action': "ENGAGE_JAMMER_SUPPRESSION",
                    'ordered_azimuth_deg': round(target_bearing, 2),
                    'target_range_meters': round(self.computed_jammer_state['range_meters'], 1),
                    'allocation_status': "OVERRIDE_ACTIVE"
                }
            else:
                # Keep active; do not interrupt weapons systems engaged in existing fire control paths
                mount_command = {
                    'mount_id': mount['mount_id'],
                    'action': "MAINTAIN_PRIMARY_MISSION_ENGAGEMENT",
                    'ordered_azimuth_deg': mount['current_azimuth'],
                    'target_range_meters': 0.0,
                    'allocation_status': "NOMINAL"
                }
            assigned_mount_commands.append(mount_command)
            
        return assigned_mount_commands

# Verification Testing Matrix Environment
if __name__ == "__main__":
    print("EXECUTING ASYMMETRIC RE-ALLOCATION MATRIX CHECK:")
    print("=" * 65)
    
    targeting_system = RadarJammerTargetingSystem(own_ship_x=0.0, own_ship_y=0.0)
    
    # Mock data packet from a consort ship located 15,000 meters East and 5000 meters North
    # Both ships detect a jamming strobe line converging onto an absolute target coordinate location
    consort_telemetry = {'x_m': 15000.0, 'y_m': 5000.0, 'strobe_deg': 315.0}
    own_strobe = 45.0  # Strobe line extends 45 degrees relative to True North
    
    jammer_coordinates = targeting_system.compute_jammer_location(own_strobe, consort_telemetry)
    print(f"Calculated Jammer Range:   {jammer_coordinates['range_meters']:.2f} Meters")
    print(f"Calculated Jammer Bearing: {jammer_coordinates['bearing_true_deg']:.2f}° True")
    
    # Inventory list matching your active shipboard ordnance allocations
    shipboard_weapons_inventory = [
        {'mount_id': 'MAIN_5IN_MK45', 'is_engaged': True,  'current_azimuth': 12.0}, # Engaged with target
        {'mount_id': 'AUX_76MM_MK75', 'is_engaged': False, 'current_azimuth': 0.0},  # Sitting idle
        {'mount_id': 'PORT_CIWS_MK15', 'is_engaged': False, 'current_azimuth': 270.0} # Sitting idle
    ]
    
    allocations = targeting_system.allocate_idle_weapons(shipboard_weapons_inventory)
    print("\nDISPATCHING TARGET OVERRIDE COMMAND DATA MATRICES:")
    for command in allocations:
        print(f"Mount: {command['mount_id']:14} | Mode: {command['allocation_status']:15} | Ordered Angle: {command['ordered_azimuth_deg']}°")
