#!/usr/bin/env python3
"""
Univac-Aegis-bridge: System Import & Validation Unit Test Suite
Dynamically tests compilation integrity across all core communication modules.
"""

import sys
import os
import unittest

# Ensure Python runtime can resolve relative paths to sister modules 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        @get_event_loop
    def test_asynchronous_retry_exhaustion_limits(self):
        """Validates that the async manager cuts loops and exits cleanly when retries are exhausted."""
        from rs485_retry_manager import AsyncRS485RetryManager
        import asyncio

        # Create a mock driver that intentionally triggers errors to stress test the wrapper
        class FaultyDriver:
            def transmit_modbus_packet_rtu(self, mask):
                raise IOError("Simulated broken copper differential line.")

        manager = AsyncRS485RetryManager(FaultyDriver(), max_retries=2, timeout_seconds=0.01)
        
        # Execute async method loop inside a synchronous test wrapper pass
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(manager.execute_transaction_with_retry(0x06))
        
        # The manager should return False to signal complete loop dropouts after exactly 2 tries
        self.assertFalse(success)

    def test_terminal_flag_parsing_bounds(self):
        """Confirms that the Typer command parser validates and catches out-of-bounds node addresses."""
        from async_typer_node import app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        
        # Scenario: Operator inputs an illegal Modbus node index address (e.g., 500)
        result = runner.invoke(app, ["--slave-id", "500"])
        
        # Verify that the infrastructure successfully flags the error and stops execution
        self.assertNotEqual(result.exit_code, 0)
        
        # Scenario: Input a valid address boundary station allocation (e.g., 32)
        # We test invocation signature structures directly without firing loops
        self.assertTrue(hasattr(app, 'registered_commands'))

    def test_modbus_crc_and_framing_integrity(self):
        """Validates that Modbus RTU frames generate mathematically correct CRC-16 arrays."""
        from modbus_framing_engine import ModbusRTUFramingEngine
        encoder = ModbusRTUFramingEngine(slave_address=0x05)
        
        # Scenario: Encode an arbitrary actuator mask state (e.g., 0x06 = pump + booster active)
        modbus_raw_adu = encoder.compile_write_coils_frame(0x06)
        
        # Verify complete structure length matches target specification
        self.assertEqual(len(modbus_raw_adu), 9)
        
        # Isolate the data components and the generated Little-Endian CRC suffix bytes
        payload_bytes = modbus_raw_adu[:7]
        crc_suffix = modbus_raw_adu[7:]
        
        # Recalculating the CRC of the payload text layer must evaluate back to the parsed signature bytes
        recalculated_crc = encoder.calculate_modbus_crc(payload_bytes)
        self.assertEqual(crc_suffix, recalculated_crc)

    def test_serial_full_duplex_outbound_masking(self):
        """Validates that correct actuator control bytes are written over the serial interface link."""
        from serial_port_listener import SerialPortMatrixBridge
        
        # Create a mock serial interface channel stub to evaluate write interception parameters
        class MockSerialBus:
            def __init__(self):
                self.write_history = []
            def write(self, data: bytes):
                self.write_history.append(data)
            def flush(self):
                pass
                
        mock_bus = MockSerialBus()
        bridge = SerialPortMatrixBridge(serial_interface_handle=mock_bus)
        
        # Scenario: Trigger a situation forcing the booster engine online immediately
        bridge.utility_engine.current_greywater_level = 1800.0 # Bounded near overflow point
        sensor_input_byte = bytes([0x08]) # Input indicates shower draw loop active (Bit 3)
        
        # Execute synchronization tick pass
        outbound_command = bridge.synchronize_and_execute_hardware_pass(sensor_input_byte)
        
        # Verify result: Outbound command must have deployed booster safety locks (Bit 2 = 0x04)
        # It must have isolated showers (Bit 0 = 0x00) and running primary pumps (Bit 1 = 0x02)
        # Expected value: 0x02 (pump) | 0x04 (booster) = 0x06
        self.assertEqual(outbound_command, 0x06)
        self.assertEqual(mock_bus.write_history[0], bytes([0x06]))

def test_dual_stage_drainage_acceleration(self):
        """Verifies pneumatic booster handles severe gravity drain bottlenecks."""
        from living_quarters_controller import AcceleratedLivingQuartersController
        controller = AcceleratedLivingQuartersController("CRITICAL_DRAIN_TEST", default_capacity_liters=1000.0)
        
        # Setup: Force well to near overflow (850 Liters)
        controller.current_greywater_level = 850.0
        relay_inputs = {"water_heater_active": True} # Showers wide open
        
        # Execute processing step
        status = controller.evaluate_utility_states(relay_inputs, target_temp_c=38.5, dt=1.0)
        
        # The primary gravity pump (1.5 L/s) could not beat the inflow (4.5 L/s)
        # Verify that the auxiliary pneumatic booster (6.5 L/s) stepped in to force clearing
        self.assertTrue(status["pneumatic_booster_relay"])
        self.assertTrue(status["showers_disabled_by_overflow"])
        self.assertLess(status["well_fill_volume_liters"], 850.0)

        def test_thermal_pid_loop_convergence(self):
        """Validates that modulating valve outputs react correctly to target temperature differentials."""
        from living_quarters_controller import AdvancedLivingQuartersController
        controller = AdvancedLivingQuartersController("TEST_VALVE_NODE")
        
        # Scenario: Output is cold (20C), target is hot (40C). Valve must open toward hot line.
        valve_pct = controller.compute_valve_pid_modulation(target_temp_c=40.0, current_temp_c=20.0, dt=1.0)
        self.assertGreater(valve_pct, 0.0)
        
        # Scenario: Output exceeds target limit (50C vs 30C). Valve must shut off hot water supply.
        valve_pct_inverse = controller.compute_valve_pid_modulation(target_temp_c=30.0, current_temp_c=50.0, dt=1.0)
        self.assertEqual(valve_pct_inverse, 0.0)

    def test_living_quarters_fluid_dynamics(self):
        """Validates hydraulic thresholding and safety isolation for shower lines."""
        from living_quarters_controller import LivingQuartersController
        
        test_controller = LivingQuartersController("TEST_MODULE")
        # Force a simulated greywater overflow state
        test_controller.current_greywater_level = 450.0
        
        # Run a single evaluation slice with high heater relay usage
        relay_flags = {"water_heater_active": True, "blast_door_secured": False}
        status = test_controller.evaluate_utility_states(relay_flags, dt=1.0)
        
        # Verify that the system automatically shut off shower lines to prevent overflows
        self.assertFalse(status["shower_valves_energized"])
        self.assertTrue(status["pneumatic_ejector_running"])

class TestUnivacNetworkLayerImports(unittest.TestCase):

    def test_matrix_processor_import(self):
        """Verifies that 5x-stacked bitwise structural decoders compile properly."""
        try:
            from univac_matrix_processor import UnivacMatrixProcessor
            processor = UnivacMatrixProcessor()
            self.assertIsNotNone(processor)
            self.assertEqual(processor.WORD_36_MASK, 0x7FFFFFFFFF)
        except ImportError as e:
            self.fail(f"Failed to resolve core matrix execution node: {str(e)}")

    def test_node_matrix_processor_import(self):
        """Validates that real-time industrial life-support fluid models evaluate correctly."""
        try:
            from univac_node_matrix_processor import UnivacNodeMatrixProcessor
            node = UnivacNodeMatrixProcessor()
            # Perform a validation calculation to verify matrix equation behaviors
            relays = node.process_discrete_relays(0x00)
            self.assertFalse(relays["exhaust_fan_active"])
        except ImportError as e:
            self.fail(f"Failed to resolve fast discrete relay tracking loop: {str(e)}")

    def test_tcp_listener_and_bridge_import(self):
        """Confirms that multi-threaded socket infrastructure elements load safely."""
        try:
            from tcp_command_listener import TCPCommandMatrixBridge
            from hardware_watchdog import ComprehensiveHardwareWatchdog
            
            # Verify class descriptor instantiation logic signatures
            watchdog = ComprehensiveHardwareWatchdog(target_frequency_hz=4.0)
            self.assertTrue(hasattr(watchdog, 'register_interface_tick'))
        except ImportError as e:
            self.fail(f"Failed to compile backend connection routing layers: {str(e)}")

if __name__ == "__main__":
    print("--- COMMENCING UNIVAC DEPLOYMENT INTEGRATION CHECKS ---")
    unittest.main()
