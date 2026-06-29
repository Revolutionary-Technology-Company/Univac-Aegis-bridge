#!/usr/bin/env python3
# File Name: hardware_watchdog.py
# Location: /src/network_layer/
# Subsystem: Asynchronous Co-Processor Thread Health & Serial Link Watchdog
"""
Univac-Aegis-bridge: Extension Module for hardware_watchdog.py
Provides low-latency stream timing protection to flag system hangs.
"""

import threading
import time
from typing import Dict, Any
import logging
from hardware_watchdog import MatrixStreamWatchdog

logger = logging.getLogger("HardwareWatchdogRouter")
logger = logging.getLogger("HardwareWatchdog")
logger = logging.getLogger("ConcurrentWatchdog")

class ComprehensiveHardwareWatchdog(MatrixStreamWatchdog):
    def __init__(self, target_frequency_hz: float = 4.0):
        # Initialize the base thread monitor
        super().__init__(target_frequency_hz=target_frequency_hz, safety_margin_multiplier=2.5)
        
        # Track independent system interface states
        self.interface_ticks = {
            "SERIAL_INTERFACE": time.time(),
            "TCP_INTERFACE": time.time()
        }

    class ConcurrentDualLineWatchdog(MatrixStreamWatchdog):
    def __init__(self, target_frequency_hz: float = 4.0):
        # Initialize parent configuration loops
        super().__init__(target_frequency_hz=target_frequency_hz, safety_margin_multiplier=2.5)
        
        # Track clock states for each independent line
        self.line_timestamps = {
            "LINE_A_PRIMARY": time.time(),
            "LINE_B_BACKUP": time.time()
        }

    def register_line_packet_clear(self, active_line_name: str):
        """
        Called by your network routing layers immediately after a packet finishes 
        processing on a specific transceiver channel.
        """
        current_time = time.time()
        if active_line_name in self.line_timestamps:
            self.line_timestamps[active_line_name] = current_time
            # Keep parent background timer reset during operational states
            self.register_heartbeat()
        else:
            logger.warning(f"Unmapped hardware channel registration attempt: {active_line_name}")

    def run(self):
        """
        Asynchronous evaluation thread scanning for concurrent line drops.
        """
        self._is_running = True
        logger.info("Concurrent Dual-Line Watchdog thread active. Monitoring lines A and B.")
        
        while self._is_running:
            time.sleep(self.expected_interval / 2.0)
            current_time = time.time()
            
            # Evaluate current timing gaps for both lines
            gap_a = current_time - self.line_timestamps["LINE_A_PRIMARY"]
            gap_b = current_time - self.line_timestamps["LINE_B_BACKUP"]
            
            # Check if BOTH links have simultaneously breached the timeout limits
            if gap_a > self.max_allowed_gap and gap_b > self.max_allowed_gap:
                self._trigger_catastrophic_fault_sequence(gap_a, gap_b)
                
    def _trigger_catastrophic_fault_sequence(self, gap_a: float, gap_b: float):
        """
        Hard safety intervention loop deployed only when all network visibility is lost.
        """
        logger.critical("🚨 !!! [CATASTROPHIC BACKPLANE ISOLATION] TOTAL NETWORK LOSS DETECTED !!!")
        logger.critical(f" -> Line A Primary Stalled: {gap_a:.3f}s (Max limit: {self.max_allowed_gap:.3f}s)")
        logger.critical(f" -> Line B Backup Stalled:  {gap_b:.3f}s (Max limit: {self.max_allowed_gap:.3f}s)")
        
        logger.critical(" -> Action: Depressurizing all tactical storage pipelines.")
        logger.critical(" -> Action: Disengaging all magnetic door strikes and locks globally.")
        logger.critical(" -> Action: Deploying mechanical failsafes to guarantee egress paths.")
        
        # Reset counters to limit output logs while the connection drops are handled
        now = time.time()
        self.line_timestamps["LINE_A_PRIMARY"] = now
        self.line_timestamps["LINE_B_BACKUP"] = now
        self.register_heartbeat()
        
    def register_interface_tick(self, interface_name: str):
        """
        Called instantly inside listener loops whenever data clears the input buffer.
        """
        current_time = time.time()
        if interface_name in self.interface_ticks:
            self.interface_ticks[interface_name] = current_time
            # Also notify parent base clock to reset the master network timeout counters
            self.register_heartbeat()
        else:
            logger.warning(f"Unrecognized diagnostic interface loop registration: {interface_name}")

    def run(self):
        """
        Asynchronous analysis loop checking for granular channel decay.
        """
        self._is_running = True
        logger.info("Advanced Interface Watchdog active. Commencing track verification scans.")
        
        while self._is_running:
            time.sleep(self.expected_interval / 2.0)
            current_time = time.time()
            
            for name, last_tick in list(self.interface_ticks.items()):
                delta_t = current_time - last_tick
                
                # Check if an isolated line has locked up or stopped reporting
                if delta_t > self.max_allowed_gap:
                    logger.critical(f"!!! [LINE FAULT TRIPPED] !!! Interface: {name} stalled for {delta_t:.3f}s")
                    self._trigger_fault_sequence(delta_t)
                    
class MatrixStreamWatchdog(threading.Thread):
    def __init__(self, target_frequency_hz: float = 4.0, safety_margin_multiplier: float = 2.5):
        """
        Sets tracking boundaries based on streaming loops.
        Default target_frequency_hz = 4.0 matching standard 250ms loops.
        """
        super().__init__()
        self.daemon = True # Allows script to shut down cleanly without thread locking
        
        # Calculate maximum permissible gap interval between ticks
        self.expected_interval = 1.0 / target_frequency_hz
        self.max_allowed_gap = self.expected_interval * safety_margin_multiplier
        
        # Synchronization parameters
        self._last_heartbeat_time = time.time()
        self._lock = threading.Lock()
        self._is_running = False

    def register_heartbeat(self) -> None:
        """
        Called externally by network interfaces every time a valid packet payload is cleared.
        Resets the timing window.
        """
        with self._lock:
            self._last_heartbeat_time = time.time()

    def run(self) -> None:
        """
        Continuous observation execution loop. Runs asynchronously from data paths.
        """
        self._is_running = True
        logger.info(f"Matrix Watchdog tracking active. Maximum allowed timeout: {self.max_allowed_gap:.3f}s")
        
        while self._is_running:
            time.sleep(self.expected_interval / 2.0) # Check twice per nominal cycle to avoid tracking delay
            
            with self._lock:
                current_time = time.time()
                time_since_last_packet = current_time - self._last_heartbeat_time
                
            if time_since_last_packet > self.max_allowed_gap:
                self._trigger_fault_sequence(time_since_last_packet)

    def stop_monitoring(self) -> None:
        """
        Clean extraction pathway to deactivate checking matrices.
        """
        self._is_running = False

    def _trigger_fault_sequence(self, true_latency: float) -> None:
        """
        Hard safety intervention execution path. Executed instantly if data flow degrades.
        """
        logger.critical("!!! [WATCHDOG TIMEOUT EXCEEDED] STREAM FAILURE ENCOUNTERED !!!")
        logger.critical(f" -> No valid telemetry packet processed for {true_latency:.3f} seconds (Max limit: {self.max_allowed_gap:.3f}s).")
        
        # Enforce fail-safe security postures immediately to protect physical infrastructure
        logger.critical(" -> Action: Forcing system configuration into [REDUCED_LIABILITY_SAFE_MODE].")
        logger.critical(" -> Action: Deploying default mechanical exit pathways and unlocking emergency egress tracks.")
        
        # Reset tracker value to prevent console flooding during long connection recovery cycles
        with self._lock:
            self._last_heartbeat_time = time.time()
            
class AsynchronousHardwareWatchdog:
    def __init__(self, critical_timeout_sec: float = 1.0):
        """
        Initializes the standalone thread safety monitor.
        critical_timeout_sec: Max allowed delay before declaring a thread frozen or dead.
        """
        self.timeout = critical_timeout_sec
        self.is_monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # Central register tracking the live timestamp updates of background nodes
        self.thread_heartbeats = {
            'NMEA_SERIAL_IN': time.time(),
            'WEAPON_BUS_IN': time.time(),
            'TCP_COMMAND_IN': time.time(),
            'MAIN_CORE_MATH': time.time()
        }
        
        # System health status flags
        self.system_faulted = False
        self.tripped_subsystems = []

    def poke_watchdog(self, thread_name: str):
        """
        Call this function inside the active loops of your background threads 
        at each cycle iteration to register a fresh, healthy heartbeat.
        """
        with self.lock:
            if thread_name in self.thread_heartbeats:
                self.thread_heartbeats[thread_name] = time.time()

    def _execute_monitor_loop(self):
        """Thread-isolated background monitoring wheel checking time stamps."""
        print(f"[WATCHDOG] Active thread check routine deployed. Timeout ceiling: {self.timeout}s")
        
        while self.is_monitoring:
            current_time = time.time()
            local_faults = []
            
            with self.lock:
                for thread_name, last_heartbeat in self.thread_heartbeats.items():
                    time_delta = current_time - last_heartbeat
                    
                    if time_delta > self.timeout:
                        local_faults.append(thread_name)
            
            # Evaluate systemic health parameters
            if local_faults:
                self.system_faulted = True
                self.tripped_subsystems = local_faults
                self._trigger_emergency_safe_mode()
            else:
                self.system_faulted = False
                self.tripped_subsystems.clear()
                
            # Run checks at a steady 10Hz frequency cadence (Every 100ms)
            time.sleep(0.1)

    def _trigger_emergency_safe_mode(self):
        """
        CRITICAL HARDWARE PROTECTION GATING:
        Executed instantly if any core serial links or math wheels stall.
        """
        print(f"\n[CRITICAL_WATCHDOG_TRIP] THREAD FREEZE DETECTED: {self.tripped_subsystems}")
        print("[WATCHDOG] FORCE-DROPPING ACTUATOR DISPATCH TO ZERO TORQUE STATE.")
        # This flag is consumed directly by the main router matrix to kill power commands

    def get_watchdog_diagnostics(self) -> dict:
        """Safe thread-locked interface to pass telemetry flags up to the router or UI."""
        current_time = time.time()
        diagnostics = {}
        
        with self.lock:
            for name, last_hb in self.thread_heartbeats.items():
                diagnostics[f"delay_{name.lower()}_sec"] = round(current_time - last_hb, 3)
                
        diagnostics['watchdog_system_faulted'] = self.system_faulted
        diagnostics['watchdog_tripped_subsystems'] = self.tripped_subsystems
        return diagnostics

    def start_watchdog(self):
        """Spins up the isolated software-defined tracking inspector thread."""
        if self.is_monitoring:
            return
        self.is_monitoring = True
        
        # Pre-seed heartbeats to current boot time to prevent instant false trips
        with self.lock:
            boot_now = time.time()
            for key in self.thread_heartbeats.keys():
                self.thread_heartbeats[key] = boot_now
                
        self.monitor_thread = threading.Thread(target=self._execute_monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_watchdog(self):
        """Gracefully secures the monitoring thread context."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print("[WATCHDOG] Safety monitoring thread secured safely.")

# Verification Simulation Environment
if __name__ == "__main__":
    print("VERIFYING WATCHDOG THREAD INTERVENTION SCHEMAS:")
    print("=" * 65)
    
    # Initialize a watchdog with a fast 0.5-second trip limit
    wd = AsynchronousHardwareWatchdog(critical_timeout_sec=0.5)
    wd.start_watchdog()
    
    # Simulate healthy processing cycles poking the monitor
    wd.poke_watchdog('MAIN_CORE_MATH')
    wd.poke_watchdog('NMEA_SERIAL_IN')
    wd.poke_watchdog('WEAPON_BUS_IN')
    wd.poke_watchdog('TCP_COMMAND_IN')
    
    print("Simulating a physical serial cable sever or thread lock up (waiting 0.7s)...")
    time.sleep(0.7)
    
    # Check health parameters after the simulated link loss window
    stats = wd.get_watchdog_diagnostics()
    print(f"Watchdog Status Code State Flag: {stats['watchdog_system_faulted']}")
    print(f"Tripped Network Subsystems:      {stats['watchdog_tripped_subsystems']}")
    
    wd.stop_watchdog()
