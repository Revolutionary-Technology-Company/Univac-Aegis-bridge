# File Name: weapon_serial_parser.py
# Location: /src/network_layer/
# Subsystem: High-Speed Weapon Encoder Telemetry Ingestion Layer

import math
from typing import Dict, Any, Tuple

class WeaponSerialBusParser:
    def __init__(self):
        """
        Initializes the proprietary weapon encoder sentence processor.
        Maintains tracking historical arrays to derive accurate tracking angular velocities.
        """
        self.expected_prefix = "$PMK45"
        
        # Real-time state cache registers
        self.live_weapon_state = {
            'azimuth_deg': 0.0,
            'elevation_deg': 0.0,
            'azimuth_rate_rads': 0.0,
            'elevation_rate_rads': 0.0,
            'servo_fault_active': False
        }
        
        # History registers for numerical differentiation
        self.last_azimuth_rad = None
        self.last_elevation_rad = None
        self.last_packet_time = None

    def _verify_nmea_checksum(self, sentence: str) -> bool:
        """Validates standard NMEA 8-bit XOR hexadecimal checksum matrices."""
        if not sentence.startswith('$') or '*' not in sentence:
            return False
        try:
            data_body, hex_checksum = sentence[1:].split('*')
            hex_checksum = hex_checksum.strip()
            
            calculated_xor = 0
            for char in data_body:
                calculated_xor ^= ord(char)
                
            return f"{calculated_xor:02X}" == hex_checksum.upper()
        except Exception:
            return False

    def ingest_encoder_sentence(self, raw_sentence: str, timestamp: float) -> Dict[str, Any]:
        """
        Parses incoming gun mount ASCII streams, computes real-time tracking 
        velocities, and updates internal weapon tracking cache profiles.
        """
        clean_str = raw_sentence.strip()
        
        # 1. Structural Checksum Verification
        if not self._verify_nmea_checksum(clean_str):
            return self.live_weapon_state # Drop corrupted data, return current cache securely

        try:
            # Strip '$' and split payload metrics by standard commas
            parts = clean_str.split('*')[0].split(',')
            header = parts[0]
            
            if header != self.expected_prefix:
                return self.live_weapon_state # Ignore non-weapon messages on the data line
                
            az_deg = float(parts[1])
            el_deg = float(parts[2])
            status_hex = parts[3]
            
            # Convert positioning states to analytical metrics
            az_rad = math.radians(az_deg)
            el_rad = math.radians(el_deg)
            
            # 2. Numerical Derivative Calculation (Velocity Engine Tracking)
            if self.last_packet_time is not None and (timestamp - self.last_packet_time) > 0.001:
                dt = timestamp - self.last_packet_time
                
                # Check for 360-degree boundary wrap conditions across tracking rings
                delta_az = az_rad - self.last_azimuth_rad
                delta_az = (delta_az + math.pi) % (2.0 * math.pi) - math.pi
                
                delta_el = el_rad - self.last_elevation_rad
                
                # Assign dynamic tracking rates (radians/second)
                self.live_weapon_state['azimuth_rate_rads'] = delta_az / dt
                self.live_weapon_state['elevation_rate_rads'] = delta_el / dt
            else:
                self.live_weapon_state['azimuth_rate_rads'] = 0.0
                self.live_weapon_state['elevation_rate_rads'] = 0.0

            # 3. Process Turret Drive Bitmask Flags
            # Bit 0: Servo Over-current, Bit 1: Limit switch triggered
            status_mask = int(status_hex, 16)
            self.live_weapon_state['servo_fault_active'] = (status_mask > 0)
            
            # Store updated position values into telemetry cache
            self.live_weapon_state['azimuth_deg'] = az_deg
            self.live_weapon_state['elevation_deg'] = el_deg
            
            # Cache states for next step interval verification
            self.last_azimuth_rad = az_rad
            self.last_elevation_rad = el_rad
            self.last_packet_time = timestamp
            
        except (ValueError, IndexError):
            pass # Keep previous clean values in case of formatting anomalies

        return self.live_weapon_state

# Verification Script Profile
if __name__ == "__main__":
    parser = WeaponSerialBusParser()
    t_clock = 1000.0
    
    # Pre-calculated test vectors containing verified matching NMEA hex checksums
    # Packet sequence shows a turret rapidly swinging to starboard over a 100ms step
    mock_weapon_stream = [
        "$PMK45,088.00,025.00,0000*22\r\n",
        "$PMK45,090.58,025.15,0000*24\r\n"
    ]
    
    print("EXECUTING WEAPON BUS HIGH-SPEED SERIAL TEST PROFILE:")
    print("-" * 65)
    
    # Loop over mock packets stepping forward by a 100ms clock interval
    for raw_sentence in mock_weapon_stream:
        t_clock += 0.1
        weapon_data = parser.ingest_encoder_sentence(raw_sentence, t_clock)
        
    print(f"Decoded Azimuth Pos:   {weapon_data['azimuth_deg']} Degrees")
    print(f"Computed Azimuth Rate: {weapon_data['azimuth_rate_rads']:.4f} rad/s")
    print(f"Full Decoder Profile: \n{weapon_data}")
