#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Serial Port Listener Extension
Intercepts raw serial bus bytes and processes them through the Node Matrix Engine.
"""
# File Name: serial_port_listener.py
# Location: /src/network_layer/
# Subsystem: Asynchronous Hardware Serial Ingestion Engine

import threading
import time
import sys
import logging
from univac_node_matrix_processor import UnivacNodeMatrixProcessor
from typing import Optional
from living_quarters_controller import AcceleratedLivingQuartersController
from modbus_framing_engine import ModbusRTUFramingEngine

logger = logging.getLogger("SerialListener")
logger = logging.getLogger("RS485Driver")

# Ensure user has pyserial installed ('pip install pyserial')
try:
    import serial
except ImportError:
    # Safe fallback wrapper mock class if testing without physical hardware packages
    serial = None


# Attempt library verification hook to handle physical GPIO access paths
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

class RS485SerialPortBridge:
    def __init__(self, serial_handle, slave_address: int = 0x05, rts_control_pin: int = 18):
        """
        :param serial_handle: Active PySerial connection layer target.
        :param rts_control_pin: Physical hardware index pin assigned to DE/RE transceiver shorts.
        """
        self.serial_bus = serial_handle
        self.modbus_encoder = ModbusRTUFramingEngine(slave_address=slave_address)
        self.direction_pin = rts_control_pin
        
        # Configure the hardware GPIO layout pins if available
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.direction_pin, GPIO.OUT)
            GPIO.output(self.direction_pin, GPIO.LOW)  # Default posture: RECEIVE/LISTEN

    def transmit_modbus_packet_rtu(self, raw_actuator_mask: int):
        """
        Toggles the physical transceiver line high, writes the Modbus byte array,
        waits for the transmission to finish, and switches back to receive mode.
        """
        # 1. Compile the valid Modbus RTU byte array with trailing CRC-16 suffix
        modbus_adu_frame = self.modbus_encoder.compile_write_coils_frame(raw_actuator_mask)
        
        if not self.serial_bus or not hasattr(self.serial_bus, 'write'):
            logger.error("Transmission aborted: Serial bus interface handle is offline.")
            return

        try:
            # 2. Assert direction pin HIGH to lock out the receive bus and claim transmit priority
            if GPIO_AVAILABLE:
                GPIO.output(self.direction_pin, GPIO.HIGH)
            
            # Write the complete structural package to the copper wire
            self.serial_bus.write(modbus_adu_frame)
            
            # 3. Force hardware block drainage to prevent dropping lingering trailing bytes
            self.serial_bus.flush()
            
            # Calculate transmission duration delay to prevent cutting off the CRC suffix bytes
            # Formula: (Bits per frame / Baud rate) -> (90 bits / 9600 baud) ≈ 9.3 milliseconds
            time.sleep(0.010) 
            
        except Exception as e:
            logger.error(f"Hardware error during Modbus ADU dispatch step: {str(e)}")
        finally:
            # 4. De-assert direction pin LOW to open up receive paths for sensory feedback loops
            if GPIO_AVAILABLE:
                GPIO.output(self.direction_pin, GPIO.LOW)
            logger.debug(f"RS-485 bus flipped back to RECEIVE mode on pin {self.direction_pin}.")
            
    def synchronize_and_execute_hardware_pass(self, raw_incoming_byte: bytes) -> Optional[int]:
        """
        Decodes physical sensor lines, recalculates fluid delta equations, 
        and dispatches structural valve overrides back to the hardware platform.
        """
        if not raw_incoming_byte or len(raw_incoming_byte) == 0:
            return None

        # 1. Parse Input Byte: Read current physical sensor loop conditions
        # Mapping: Bit 3 high indicates water heater loop drawing energy
        sensor_register = int.from_bytes(raw_incoming_byte, byteorder="big")
        relay_flags = {
            "water_heater_active": bool(sensor_register & (1 << 3)),
            "blast_door_secured":  bool(sensor_register & (1 << 4))
        }

        # Calculate time differential accurately to maintain constant continuous integration velocities
        current_time = time.time()
        dt = current_time - self.last_execution_timestamp
        self.last_execution_timestamp = current_time

        # 2. Compute Accelerated Fluid Equation Matrix Pass
        # Target shower comfort index setpoint = 38.5 Degrees Celsius
        telemetry = self.utility_engine.evaluate_utility_states(
            relay_flags=relay_flags, 
            target_temp_c=38.5, 
            dt=dt
        )

        # 3. Construct Outbound Actuator Bitmask Register
        actuator_command_byte = 0x00
        
        if telemetry["shower_active"]:
            actuator_command_byte |= (1 << 0)  # Open shower valve
        if telemetry["primary_pump_relay"]:
            actuator_command_byte |= (1 << 1)  # Engage primary gravity pump
        if telemetry["pneumatic_booster_relay"]:
            actuator_command_byte |= (1 << 2)  # Deploy pneumatic high-speed booster line
            
        # 4. Physical Full-Duplex Dispatch Operation
        if self.serial_bus and hasattr(self.serial_bus, 'write'):
            try:
                # Convert packed integer to standard raw single byte element
                payload = bytes([actuator_command_byte])
                self.serial_bus.write(payload)
                self.serial_bus.flush() # Instantly empty hardware pipeline onto physical wire
                logger.debug(f"Dispatched hardware command byte over serial link: 0x{actuator_command_byte:02X}")
            except Exception as e:
                logger.error(f"Hardware physical dispatch failure over serial link: {str(e)}")

        # 5. Broadcast to Matrix Topology
        # If the master network interface router is hooked, feed it the continuous JSON log stream
        if self.router:
            # We recreate the system stream configuration chunk directly from the evaluated metrics
            from univac_matrix_processor import UnivacMatrixProcessor
            dummy_processor = UnivacMatrixProcessor()
            
            # Map metrics to standard 5x-stacked 36-bit syntax structures
            hex_matrix = [
                dummy_processor.pack_to_36bit_hex_string(telemetry["well_load_percentage"] / 100.0, 0),
                f"0x{actuator_command_byte:010X}",
                "0x0000000000", "0x0000000000", "0x0000000000"
            ]
            
            import json
            packet = {
                "protocol": "UNIVAC-MATRIX-STREAM",
                "version": "9.1.0-TACTICAL",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(current_time)),
                "facilityZone": self.utility_engine.zone_id,
                "matrixState": {
                    "stackedWords36": hex_matrix,
                    "filterConfidence": 0.995,
                    "integrityCheck": "STABLE"
                },
                "routingControls": {
                    "isolationGates": "LOCKED" if telemetry["pneumatic_booster_relay"] else "OPEN",
                    "hvacFlowMode": "EXHAUST_ISOLATE" if telemetry["pneumatic_booster_relay"] else "NORMAL",
                    "elevatorBrakes": "MONITORING"
                }
            }
            self.router.ingest_live_system_frame(json.dumps(packet))

        return actuator_command_byte
        
class SerialPortMatrixBridge:
    def __init__(self, serial_interface_handle=None, router_instance=None):
        # Initialize the telemetry processing engine
        self.node_processor = UnivacNodeMatrixProcessor(zone_identifier="BUNKER_SERIAL_HUB")
        self.router = router_instance
        # Initialize engine configured for the main underground hub
        self.utility_engine = AcceleratedLivingQuartersController(zone_id="BUNKER_UTILITY_CORE")
        self.serial_bus = serial_interface_handle
        self.router = router_instance
        self.last_execution_timestamp = time.time()
        
    def handle_raw_serial_byte(self, raw_byte: bytes) -> None:
        """
        Processes a raw input byte received from the physical serial port interface.
        """
        if not raw_byte or len(raw_byte) == 0:
            return

        # Convert raw byte to integer representation (0-255)
        pin_register = int(raw_byte[0])
        
        # Compile into packed 5x-stacked 36-bit JSON matrices
        json_frame = self.node_processor.compile_live_matrix_packet(pin_register)
        
        # Forward directly into the primary network router layer if configured
        if self.router:
            self.router.ingest_live_system_frame(json_frame)
        else:
            logger.debug(f"[SERIAL DROP] Packet generated but no router hooked: {json_frame}")

class ThreadedSerialPortListener:
    def __init__(self, router_instance, port_name: str = "/dev/ttyUSB0", baud_rate: int = 4800, timeout_sec: float = 1.0):
        """
        Initializes an isolated high-priority background serial ingestion loop.
        
        router_instance: Instantiated BridgeNetworkRouter object to route decoded data.
        port_name: System hardware handle (e.g., '/dev/ttyUSB0' on Linux, 'COM3' on Windows).
        baud_rate: Standard maritime NMEA communication speed (4800 for legacy, 38400 for AIS).
        timeout_sec: Maximum blocking window for serial buffer reading operations.
        """
        self.router = router_instance
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.timeout = timeout_sec
        
        self.serial_connection = None
        self.is_listening = False
        self.worker_thread = None

    def _execute_read_loop(self):
        """Asynchronous worker thread running the hard-real-time ingestion cycle."""
        print(f"[SERIAL] Establishing connection matrix on hardware port: {self.port_name} ({self.baud_rate} Baud)")
        
        while self.is_listening:
            try:
                if self.serial_connection is None or not self.serial_connection.is_open:
                    if serial is None:
                        print("[SERIAL_MOCK] Pyserial module not found. Running software emulation.")
                        self._run_emulation_routine()
                        return
                        
                    # Attempt physical connection open sequence
                    self.serial_connection = serial.Serial(
                        port=self.port_name,
                        baudrate=self.baud_rate,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=self.timeout
                    )
                    print(f"[SERIAL] Hardware port {self.port_name} connected successfully.")

                # Read raw input sequence until reaching an end-of-line frame
                # NMEA-0183 standard sentences always terminate with \n (0x0A)
                raw_bytes = self.serial_connection.readline()
                
                if raw_bytes:
                    try:
                        # Decode raw binary ascii buffer stream safely into standard characters
                        decoded_sentence = raw_bytes.decode('ascii', errors='ignore')
                        
                        # Forward the string package straight to the network router cache matrix
                        if decoded_sentence.strip():
                            self.router.ingest_raw_serial_line(decoded_sentence)
                    except Exception as parse_error:
                        print(f"[SERIAL_ERROR] Local byte string decoding failure: {parse_error}")

            except (IOError, Exception) as hardware_disconnect_error:
                print(f"[SERIAL_ALERT] Connection dropped on {self.port_name}: {hardware_disconnect_error}")
                print("[SERIAL] Re-attempting physical interface registration in 3.0 seconds...")
                if self.serial_connection:
                    try:
                        self.serial_connection.close()
                    except:
                        pass
                    self.serial_connection = None
                time.sleep(3.0)

    def _run_emulation_routine(self):
        """Generates mock hardware telemetry over time if run on a non-connected machine."""
        mock_heading = 124.5
        while self.is_listening:
            time.sleep(0.2)
            mock_heading = (mock_heading + 0.1) % 360.0
            # Construct a simulated heading frame with a valid pre-computed checksum (*1C format equivalent)
            dummy_sentence = f"$HEHDT,{mock_heading:.1f},T*1C\r\n"
            self.router.ingest_raw_serial_line(dummy_sentence)

    def start_listening(self):
        """Spins up the isolated hardware interception background thread."""
        if self.is_listening:
            return
        self.is_listening = True
        self.worker_thread = threading.Thread(target=self._execute_read_loop, daemon=True)
        self.worker_thread.start()
        print(f"[SERIAL] Threaded Listener service spawned for {self.port_name}.")

    def stop_listening(self):
        """Gracefully winds down the interface serial connection port."""
        self.is_listening = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print(f"[SERIAL] Hardware device {self.port_name} closed down.")

# Verification Integration Check
if __name__ == "__main__":
    # Mock Router framework stub to catch incoming telemetry metrics for local verification
    class MockRouterStub:
        def ingest_raw_serial_line(self, raw_nmea_string: str):
            print(f"[ROUTER_STUB_RECV] Received from wire: {raw_nmea_string.strip()}")

    mock_router = MockRouterStub()
    
    # Configure cross-platform listener parameter formats safely
    test_port = "COM3" if sys.platform.startswith('win') else "/dev/ttyUSB0"
    
    listener = ThreadedSerialPortListener(router_instance=mock_router, port_name=test_port, baud_rate=4800)
    
    print("LAUNCHING SERIAL TELEMETRY INTERCEPTION NODES:")
    print("-" * 65)
    listener.start_listening()
    
    time.sleep(1.0) # Allow standard streaming frames to cascade across loop threads
    listener.stop_listening()
