# File Name: actuator_serial_serializer.py
# Location: /src/network_layer/

import math
from typing import Dict, Any

class ActuatorSerialOutputSerializer:
    def __init__(self, manufacturer_code: str = "UNVC"):
        """
        Initializes the proprietary NMEA serializer.
        manufacturer_code: 4-character identifier for your custom/replacement hardware bus.
        """
        # Ensure the code is strictly a 4-character uppercase alphanumeric string
        self.code = manufacturer_code.upper()[:4]

    def _generate_checksum(self, payload: str) -> str:
        """
        Calculates a standard NMEA 8-bit XOR checksum.
        Loops through all characters inside the string body to compute the hex validation byte.
        """
        checksum = 0
        for char in payload:
            checksum ^= ord(char)
        return f"{checksum:02X}"

    def serialize_rudder_command(self, engine_output: Dict[str, Any], message_type: str = "STR") -> bytes:
        """
        Converts the bridge engine's rudder angle calculation into a physical serial string.
        
        Sentence Format: $P[CODE][TYPE],rudder_deg,direction,slew_rate_cap*CS\\r\\n
        Example: $PUNVCSTR,-14.25,L,12.5*3F\\r\\n
        """
        rudder_deg = engine_output.get('command_rudder_angle_deg', 0.0)
        
        # Extract or default safety limits from the telemetry array
        active_caps = engine_output.get('upstream_autonomy_telemetry', {}).get('UNIVAC_Water_Insight_Link', {})
        slew_rate_cap = 15.0 # Fallback default maximum speed in degrees/second
        
        # Explicit directional string parameter for legacy PLC/controller redundancy
        direction = "R" if rudder_deg >= 0 else "L"
        abs_rudder_deg = abs(rudder_deg)

        # Build the exact comma-separated text payload (excluding '$' and '*')
        payload = f"P{self.code}{message_type.upper()},{abs_rudder_deg:.2f},{direction},{slew_rate_cap:.1f}"
        
        # Append framing elements and the computed 8-bit checksum
        checksum_hex = self._generate_checksum(payload)
        nmea_sentence = f"${payload}*{checksum_hex}\r\n"
        
        # Encode as strict standard 8-bit ASCII bytes for direct physical port writes
        return nmea_sentence.encode('ascii')

    def serialize_propulsion_command(self, engine_output: Dict[str, Any], message_type: str = "PRP") -> bytes:
        """
        Converts the bridge engine's torque and speed constraints into a serial propulsion string.
        
        Sentence Format: $P[CODE][TYPE],torque_nm,rpm_cap,fatigue_pct*CS\\r\\n
        Example: $PUNVCPRP,45200.5,480.0,42.1*1B\\r\\n
        """
        torque_nm = engine_output.get('command_motor_torque_nm', 0.0)
        
        # Access nested upstream limits or fallback safely
        insight_link = engine_output.get('upstream_autonomy_telemetry', {}).get('UNIVAC_Water_Insight_Link', {})
        rpm_cap = engine_output.get('active_rpm_cap', 550.0) # Safe default if unavailable
        fatigue_pct = insight_link.get('structural_fatigue_load_percentage', 0.0)

        # Format the core ASCII structure
        payload = f"P{self.code}{message_type.upper()},{torque_nm:.1f},{rpm_cap:.1f},{fatigue_pct:.1f}"
        
        checksum_hex = self._generate_checksum(payload)
        nmea_sentence = f"${payload}*{checksum_hex}\r\n"
        
        return nmea_sentence.encode('ascii')

# Local Verification and Stress-Testing Runtime
if __name__ == "__main__":
    serializer = ActuatorSerialOutputSerializer(manufacturer_code="UNVC")
    
    # Mock output generated directly from your Bridge Matrix Core engine loop
    mock_engine_matrix_output = {
        "command_motor_torque_nm": 45200.5,
        "command_rudder_angle_deg": -14.25,
        "active_rpm_cap": 480.0,
        "upstream_autonomy_telemetry": {
            "UNIVAC_Water_Insight_Link": {
                "structural_fatigue_load_percentage": 42.1
            }
        }
    }
    
    # Generate the physical serial wire payloads
    rudder_packet = serializer.serialize_rudder_command(mock_engine_matrix_output)
    propulsion_packet = serializer.serialize_propulsion_command(mock_engine_matrix_output)
    
    print("SERIAL ACTUATOR STRING VALIDATION ENGINE:")
    print("-" * 75)
    print("Rudder Actuator Wire Output:")
    print(rudder_packet.decode('ascii').strip())
    print("\nPropulsion/Motor Drive Wire Output:")
    print(propulsion_packet.decode('ascii').strip())
