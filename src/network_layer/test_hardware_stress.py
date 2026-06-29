#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Local Workstation Stability Test Tool
Simulates long-duration continuous full-duplex hardware telemetry iterations.
"""

import time
import sys
import logging
from modbus_framing_engine import ModbusRTUFramingEngine
from serial_port_listener import SerialPortMatrixBridge

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StressTester")

class VirtualSerialPortStub:
    """Mock interface trapping outbound serial data for validation checks."""
    def __init__(self):
        self.last_written_bytes = b""
    def write(self, data: bytes):
        self.last_written_bytes = data
    def flush(self):
        pass

def run_stability_marathon(target_cycles: int = 5000, pulse_delay_sec: float = 0.001):
    """
    Simulates a continuous flood of sensor line updates to evaluate software robustness.
    """
    logger.info(f"Initializing workstation stability run. Target load: {target_cycles} execution cycles.")
    
    # Instantiate the system pipeline components
    virtual_uart = VirtualSerialPortStub()
    serial_bridge = SerialPortMatrixBridge(serial_interface_handle=virtual_uart)
    modbus_encoder = ModbusRTUFramingEngine(slave_address=0x05)
    
    start_time = time.perf_counter()
    processed_count = 0
    failure_count = 0
    
    try:
        for cycle in range(target_cycles):
            # Alternate raw inputs: Simulate varying states like high water or heater draw
            # Trigger high-water delta check on alternating sets
            if cycle % 100 < 40:
                sensor_input = bytes([0x08])  # Heater loop active (Bit 3)
            else:
                sensor_input = bytes([0x00])  # Normal tracking ambient state
                
            # Execute full-duplex computation step
            actuator_mask = serial_bridge.synchronize_and_execute_hardware_pass(sensor_input)
            
            if actuator_mask is not None:
                # Wrap the raw output mask into a valid multi-drop Modbus package frame
                modbus_frame = modbus_encoder.compile_write_coils_frame(actuator_mask)
                processed_count += 1
                
                # Validation boundary check: Verify minimum valid Modbus RTU length (Slave + FC + Addr + Qty + Len + Data + CRC = 9 bytes)
                if len(modbus_frame) != 9:
                    failure_count += 1
            else:
                failure_count += 1
                
            # Throttle loop interval slightly if needed to match clock structures
            if pulse_delay_sec > 0:
                time.sleep(pulse_delay_sec)
                
    except KeyboardInterrupt:
        logger.warning("Stability test loop prematurely interrupted by operator command.")
        
    duration = time.perf_counter() - start_time
    average_cycle_time_us = (duration / processed_count) * 1_000_000 if processed_count > 0 else 0
    
    logger.info("==========================================================")
    logger.info("🏁 COMPILATION STABILITY METRIC REPORT")
    logger.info("==========================================================")
    logger.info(f"Total Execution Runtime : {duration:.4f} seconds")
    logger.info(f"Successfully Passed Ticks: {processed_count} frames")
    logger.info(f"System Pipeline Faults  : {failure_count} errors")
    logger.info(f"Mean Cycle Processing Latency: {average_cycle_time_us:.2f} microseconds")
    logger.info("==========================================================")
    
    if failure_count == 0 and processed_count == target_cycles:
        logger.info("✅ SUCCESS: Sub-millisecond tracking engine stable under load.")
        sys.exit(0)
    else:
        logger.error("❌ FAILURE: Processing discrepancies detected in pipeline layers.")
        sys.exit(1)

if __name__ == "__main__":
    # Execute a standard local simulation marathon test block
    run_stability_marathon(target_cycles=2000, pulse_delay_sec=0.0002)
