# File Name: univac_mac_aligner.py
# Location: /src/network_layer/
# Subsystem: Dynamic Mainframe VIN-Style MAC Address Alignment & Actuator Router Engine

import re
import time
from typing import Dict, Any, Tuple

class UnivacMacAlignmentEngine:
    def __init__(self):
        """Initializes the multi-generational tactical vessel address matrix."""
        self.vessel_oui_catalog = {
            'EARLY_AEGIS_CRUISER':   '00:00:A3', # CG-47 class mainframes
            'EARLY_AEGIS_DESTROYER': '00:01:4A', # DDG-51 class mainframes
            'ENTERPRISE_CARRIER':     '00:1D:6E', # CVN-65 / Heavy Fleet
            'PRE_AEGIS_COMBATTANT':  '00:50:2A', # CP-642B legacy units
            'PRE_AEGIS_AUXILIARY':   '00:D0:6B'  # Auxiliary / Shore Base networks
        }
        
        self.active_alignment_state = {
            'target_vessel_class': 'EARLY_AEGIS_DESTROYER',
            'computed_alignment_mac': '00:01:4A:00:00:00',
            'hardware_lock_secured': False,
            'timestamp_synchronized': time.time()
        }

    def compute_lowest_possible_handshake_mac(self, vessel_class_key: str, device_id: int, mainframe_id: int, switch_depth: int = 0, switch_port: int = 0) -> dict:
        """
        Calculates the definitive dynamic VIN-style MAC address token required
        to align the local interface identity and bypass legacy hardware synchronization locks.
        """
        sanitized_key = vessel_class_key.upper().strip()
        oui_prefix = self.vessel_oui_catalog.get(sanitized_key, '00:00:A3')
        
        # Enforce physical hardware structural boundaries
        bounded_device = max(0, min(14, device_id))      # Max 15 peripheral devices allowed
        bounded_mainframe = max(0, min(3, mainframe_id)) # Mainframe array index bounds
        bounded_depth = max(0, min(255, switch_depth))
        bounded_port = max(0, min(254, switch_port))     # 254 usable switch ports
        
        # --- EXECUTE THE RADAR WEAPONS HARDWARE BITMASK LOGIC ---
        # Bit 0: Device index value
        bit_0 = bounded_device & 1
        
        # Bit 1: Mainframe index value
        bit_1 = bounded_mainframe & 1
        
        # Bit 2: Mainframe matching latch bit (Must duplicate Bit 0 of the target device)
        bit_2 = bit_0
        
        # Compile the final 8-bit tracking register byte (Octet 6)
        octet_6_val = (bit_2 << 2) | (bit_1 << 1) | bit_0
        # ────────────────────────────────────────────────────────
        
        # Format the final components into standard 2-digit hexadecimal address segments
        octet_4_hex = f"{bounded_depth:02X}"
        octet_5_hex = f"{bounded_port:02X}"
        octet_6_hex = f"{octet_6_val:02X}"
        
        compiled_mac = f"{oui_prefix}:{octet_4_hex}:{octet_5_hex}:{octet_6_hex}"
        
        # A valid hardware lock requires matching bits on Bit 0 and Bit 2
        is_locked = (bit_0 == bit_2)

        self.active_alignment_state = {
            'target_vessel_class': sanitized_key,
            'computed_alignment_mac': compiled_mac,
            'hardware_lock_secured': is_locked,
            'timestamp_synchronized': time.time()
        }
        
        return self.active_alignment_state.copy()

# Local Diagnostics Pass Profile Environment
if __name__ == "__main__":
    aligner = UnivacMacAlignmentEngine()
    print("VERIFYING TACTICAL VIN-STYLE MAC ALIGNMENT ARRAYS:")
    print("=" * 70)
    
    # Test 1: Query the lowest possible handshake MAC for an early Aegis Cruiser (CG-47)
    # Direct-wired (no switches, depth=0, port=0), targeting Device 1 on Mainframe 0
    res_1 = aligner.compute_lowest_possible_handshake_mac(
        vessel_class_key='EARLY_AEGIS_CRUISER',
        device_id=1,
        mainframe_id=0,
        switch_depth=0,
        switch_port=0
    )
    print(f"Test 1 (Cruiser Boot Link) -> MAC: {res_1['computed_alignment_mac']} | Lock Secured: {res_1['hardware_lock_secured']}")
    
    # Test 2: Query an advanced route passing through a stacked switch network on a Carrier (CVN-65)
    # Switch Depth active, tracking Device 0 on Mainframe 1 running through Port 42
    res_2 = aligner.compute_lowest_possible_handshake_mac(
        vessel_class_key='ENTERPRISE_CARRIER',
        device_id=0,
        mainframe_id=1,
        switch_depth=1,
        switch_port=42
    )
    print(f"Test 2 (Carrier Switch Link) -> MAC: {res_2['computed_alignment_mac']} | Lock Secured: {res_2['hardware_lock_secured']}")
