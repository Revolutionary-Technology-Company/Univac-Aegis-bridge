# File Name: shore_weapon_serializer.py
# Location: /src/network_layer/
# Subsystem: High-Speed Ship-to-Shore Joint Weapon System Serializer

import math
from typing import Dict, Any, List

class ShoreWeaponSystemSerializer:
    def __init__(self, prefix_code: str = "PUNVC"):
        """
        Initializes the proprietary ship-to-shore joint fire control protocol engine.
        prefix_code: 5-character proprietary identifier string layer.
        """
        self.prefix = f"{prefix_code.upper()[:5]}SHR"
        
        # Mapping index table linking shore installations to target numeric registers
        self.shore_battery_catalog = {
            'SHORE_BATTERY_ALPHA': 101,
            'COASTAL_VLS_CELL_MATRIX': 102
        }

    def _calculate_8bit_xor_checksum(self, payload: str) -> str:
        """Computes a standard industrial NMEA text string validation byte."""
        checksum = 0
        for char in payload:
            checksum ^= ord(char)
        return f"{checksum:02X}"

    def serialize_shore_fire_commands(self, high_speed_target_buffer: dict, active_shore_weapons: List[dict]) -> List[bytes]:
        """
        Ingests the ship's thread-isolated target matrix, checks if the remote link is active,
        and compiles the direct-fire execution strings for the shore weapon servo drives.
        """
        outbound_shore_packets = []
        
        # Extract the ship's high-speed independent targeting states
        target_bearing = high_speed_target_buffer.get('target_bearing_deg', 0.0)
        target_elevation = high_speed_target_buffer.get('current_elevation_deg', 0.0)
        target_locked = high_speed_target_buffer.get('is_target_locked', False)
        
        for weapon in active_shore_weapons:
            raw_id_string = weapon.get('shore_station_id', 'UNKNOWN')
            numeric_station_id = self.shore_battery_catalog.get(raw_id_string, 999)
            
            link_connected = weapon.get('umbilical_link_connected', False)
            navy_fire_authorize = weapon.get('navy_combat_release_cleared', False)
            
            # Authorization Gate: Only fire if connection is active, target is locked, and Navy has cleared the code
            if link_connected and target_locked and navy_fire_authorize:
                interlock_bit = 1  # 1 = Remote Ship Fire Authorized (Remote Override Active)
            else:
                interlock_bit = 0  # 0 = Local Base Safe Hold (Bypass Prevented)

            # Assemble the absolute text payload string (excluding leading '$' and trailing '*')
            payload = f"{self.prefix},{numeric_station_id},{target_bearing:.2f},{target_elevation:.2f},{interlock_bit}"
            
            # Append framing boundaries and hex checksum validations
            checksum_hex = self._calculate_8bit_xor_checksum(payload)
            final_sentence = f"${payload}*{checksum_hex}\r\n"
            
            # Convert directly into ASCII byte stream arrays to bypass string translation latencies
            outbound_shore_packets.append(final_sentence.encode('ascii'))
            
        return outbound_shore_packets

# Local Verification and Loop Test Profile Environment
if __name__ == "__main__":
    serializer = ShoreWeaponSystemSerializer(prefix_code="PUNVC")
    
    # Mock data snapshot mimicking the ship's high-speed memory tracking register state
    mock_high_speed_buffer = {
        'target_bearing_deg': 142.55,
        'current_elevation_deg': 22.40,
        'is_target_locked': True
    }
    
    # Inventory matrix checking your active land-based battery link parameters
    mock_shore_battery_links = [
        {
            'shore_station_id': 'SHORE_BATTERY_ALPHA',
            'umbilical_link_connected': True,
            'navy_combat_release_cleared': True
        },
        {
            'shore_station_id': 'COASTAL_VLS_CELL_MATRIX',
            'umbilical_link_connected': False, # Cable disconnected, should trigger safe hold
            'navy_combat_release_cleared': True
        }
    ]
    
    print("JOINT SHIP-TO-SHORE TARGET LINK PROTOCOL TEST:")
    print("=" * 75)
    
    binary_packets = serializer.serialize_shore_fire_commands(mock_high_speed_buffer, mock_shore_battery_links)
    
    for idx, packet in enumerate(binary_packets):
        print(f"Frame {idx} Outbound Shore Wire Payload String:")
        print(packet.decode('ascii').strip())
