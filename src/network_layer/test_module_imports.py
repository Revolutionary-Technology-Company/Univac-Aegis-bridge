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
