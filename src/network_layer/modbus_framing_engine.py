#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Modbus RTU Framing & CRC Engine
Packages raw byte registers into valid multi-drop RS-485 industrial frames.
"""

import logging

logger = logging.getLogger("ModbusFraming")

class ModbusRTUFramingEngine:
    def __init__(self, slave_address: int = 0x05):
        """
        :param slave_address: Target physical station node ID on the RS-485 bus.
        """
        self.slave_address = slave_address

    @staticmethod
    def calculate_modbus_crc(data: bytes) -> bytes:
        """
        Computes the standard 16-bit Modbus CRC polynomial (0xA001) using bitwise shifts.
        Returns 2 bytes in Little-Endian configuration (LSB, MSB).
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    def compile_write_coils_frame(self, actuator_byte: int) -> bytes:
        """
        Encapsulates the 8-bit relay mask using Function Code 15 (Write Multiple Coils).
        Maps to digital coil outputs starting at reference address 0x0000.
        """
        # Build standard Modbus Protocol Data Unit (PDU) Header
        function_code = 0x0F          # FC15: Write Multiple Coils
        starting_address_hi = 0x00
        starting_address_lo = 0x00    # Target Coil 0
        quantity_of_coils_hi = 0x00
        quantity_of_coils_lo = 0x05   # Writing 5 active relay channels
        byte_count = 0x01             # All 5 bits fit into a single data byte
        
        # Assemble Application Data Unit (ADU) payload skeleton
        adu_skeleton = bytes([
            self.slave_address,
            function_code,
            starting_address_hi, starting_address_lo,
            quantity_of_coils_hi, quantity_of_coils_lo,
            byte_count,
            actuator_byte & 0x1F      # Mask out reserved diagnostic upper bits
        ])
        
        # Calculate and append CRC-16 check suffix
        crc_suffix = self.calculate_modbus_crc(adu_skeleton)
        return adu_skeleton + crc_suffix
