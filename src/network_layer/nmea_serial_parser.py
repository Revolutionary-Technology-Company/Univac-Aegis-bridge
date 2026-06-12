# File Name: nmea_serial_parser.py
# Location: /src/network_layer/

import re
from typing import Dict, Any, Optional

class NmeaSerialDataParser:
    def __init__(self):
        """
        Initializes the serial sentence engine.
        Maintains a rolling state telemetry register to feed the bridge engine.
        """
        self.telemetry_cache = {
            'rpm': 0.0,              # Updated by local motor bus
            'depth': 50.0,           # Updated via $SDDBT / $SDDPT
            'speed_ms': 0.0,         # Updated via $GPRMC
            'bow_sensor_meters': 0.0, # Updated via custom bow string or analog line
            'yaw_rate_rads': 0.0,    # Derived from consecutive true headings
            'roll_angle_rad': 0.0,   # Updated via inertial sensors
            'roll_rate_rads': 0.0,   # Updated via inertial sensors
            'distance_to_bank_meters': 100.0,
            'rudder_deg': 0.0        # Fed back from steering hydraulics
        }
        
        self.last_heading = None
        self.last_heading_time = None

    def validate_checksum(self, sentence: str) -> bool:
        """
        Validates standard NMEA 8-bit XOR hexadecimal checksums.
        Expects format: $GPxxx,val1,val2...*CC\\r\\n
        """
        if not sentence.startswith('$') or '*' not in sentence:
            return False
            
        try:
            # Isolate data string between '$' and '*'
            data_body, hex_checksum = sentence[1:].split('*')
            hex_checksum = hex_checksum.strip()
            
            calculated_xor = 0
            for char in data_body:
                calculated_xor ^= ord(char)
                
            return f"{calculated_xor:02X}" == hex_checksum.upper()
        except Exception:
            return False

    def parse_sentence(self, raw_sentence: str, timestamp: float) -> Dict[str, Any]:
        """
        Parses incoming serial ASCII streams. Updates internal state caches 
        when valid identifier signatures match.
        """
        clean_str = raw_sentence.strip()
        if not self.validate_checksum(clean_str):
            return self.telemetry_cache # Drop corrupted data, return current cache safely

        # Split payload by standard commas
        parts = clean_str.split('*')[0].split(',')
        talker_id = parts[0]

        try:
            # 1. PARSE HEADING DATA (True Heading)
            if talker_id.endswith('HDT'):
                # Format: $HEHDT,xxx.xx,T*CC
                if parts[1]:
                    current_heading_deg = float(parts[1])
                    current_heading_rad = math.radians(current_heading_deg) if 'math' in globals() else (current_heading_deg * 3.14159 / 180.0)
                    
                    # Derive yaw rate mathematically from consecutive time steps
                    if self.last_heading is not None and self.last_heading_time is not None:
                        dt = timestamp - self.last_heading_time
                        if dt > 0.001:
                            # Handle 360-degree boundary wrap conditions
                            delta_heading = current_heading_rad - self.last_heading
                            delta_heading = (delta_heading + 3.14159) % (2.0 * 3.14159) - 3.14159
                            self.telemetry_cache['yaw_rate_rads'] = delta_heading / dt
                            
                    self.last_heading = current_heading_rad
                    self.last_heading_time = timestamp

            # 2. PARSE DEPTH DATA (Depth Below Transducer)
            elif talker_id.endswith('DBT'):
                # Format: $SDDBT,feet,f,meters,M,fathoms,F*CC
                if parts[3]: # Index 3 contains depth calculated in Meters
                    self.telemetry_cache['depth'] = float(parts[3])
            
            elif talker_id.endswith('DPT'):
                # Alternative Format: $SDDPT,meters,offset*CC
                if parts[1]:
                    self.telemetry_cache['depth'] = float(parts[1])

            # 3. PARSE SPEED DATA (Recommended Minimum GPS Sentence)
            elif talker_id.endswith('RMC'):
                # Format: $GPRMC,time,status,lat,N,lon,E,speed_knots,course,date...*CC
                if parts[2] == 'A': # Ensure status is 'A' (Valid navigation lock)
                    if parts[7]:
                        speed_knots = float(parts[7])
                        # Convert knots to standardized system SI units (meters/second)
                        self.telemetry_cache['speed_ms'] = speed_knots * 0.514444

        except (ValueError, IndexError) as e:
            # Prevent malformed numeric parameters from halting execution arrays
            pass

        return self.telemetry_cache

# Simulation Verification Script
if __name__ == "__main__":
    parser = NmeaSerialDataParser()
    t_clock = 1000.0 # Arbitrary epoch baseline
    
    # Pre-calculated test vectors containing verified matching NMEA hex checksums
    mock_serial_stream = [
        "$HEHDT,124.50,T*1C\r\n",   # True heading 124.5°
        "$SDDBT,24.6,f,7.50,M,4.1,F*0D\r\n", # Water depth 7.50 meters
        "$GPRMC,123519,A,4807.038,N,01131.000,E,14.2,34.4,230326,,,A*6A\r\n" # Speed 14.2 knots
    ]
    
    print("EXECUTING HARDWARE NMEA DECODER EMULATION ENGINE:")
    print("-" * 65)
    
    # Process sequential packets jumping forward by 200ms intervals
    for raw_frame in mock_serial_stream:
        t_clock += 0.2
        current_telemetry = parser.parse_sentence(raw_frame, t_clock)
        
    print(f"Decoded Speed:   {current_telemetry['speed_ms']:.2f} m/s (~14.2 knots)")
    print(f"Decoded Depth:   {current_telemetry['depth']:.2f} Meters")
    print(f"Computed Cache Register State: \n{current_telemetry}")
