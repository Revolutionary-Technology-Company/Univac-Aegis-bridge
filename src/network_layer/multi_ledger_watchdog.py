# File Name: multi_ledger_watchdog.py
# Location: /src/network_layer/
# Subsystem: Asynchronous Multi-Ledger Logging Safety and Thread Watchdog

import threading
import time
import os
from typing import Dict, Any, List

class MultiLedgerHardwareWatchdog:
    def __init__(self, write_timeout_sec: float = 2.0, log_directory: str = "logs"):
        """
        Initializes the multi-ledger data integrity supervisor.
        write_timeout_sec: Maximum safe delay allowed between successful file append operations.
        """
        self.timeout = write_timeout_sec
        self.log_dir = os.path.join(os.path.dirname(__file__), "..", log_directory)
        self.is_monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # Central register tracking the live write activity timestamps of distinct logging classes
        self.ledger_heartbeats = {
            'FLAG_HALYARD_AUDIT': time.time(),
            'MARPOL_BILGE_AUDIT': time.time(),
            'MISSION_TELEMETRY': time.time()
        }
        
        # Track the memory buffer queue sizes of each logger module to detect I/O congestion
        self.ledger_queue_depths = {
            'FLAG_HALYARD_AUDIT': 0,
            'MARPOL_BILGE_AUDIT': 0,
            'MISSION_TELEMETRY': 0
        }

        self.system_faulted = False
        self.tripped_ledgers = []

    def log_write_success(self, ledger_name: str, active_queue_size: int):
        """
        Call this function inside the file-writing worker loops of your loggers 
        whenever a row is successfully added to a CSV file.
        """
        sanitized_name = ledger_name.upper().strip()
        with self.lock:
            if sanitized_name in self.ledger_heartbeats:
                self.ledger_heartbeats[sanitized_name] = time.time()
                self.ledger_queue_depths[sanitized_name] = active_queue_size

    def _execute_integrity_checker_loop(self):
        """Asynchronous worker thread running the hard-real-time compliance checks."""
        print(f"[WATCHDOG] Multi-ledger compliance monitor active. Write window ceiling: {self.timeout}s")
        
        while self.is_monitoring:
            current_time = time.time()
            local_faults = []
            
            with self.lock:
                for ledger_name, last_write_time in self.ledger_heartbeats.items():
                    time_delta = current_time - last_write_time
                    queue_depth = self.ledger_queue_depths[ledger_name]
                    
                    # Fault Condition 1: Thread has pending data but has failed to write to disk
                    # Fault Condition 2: Memory queue depth exceeds structural safety threshold (overloaded buffer)
                    if (time_delta > self.timeout and queue_depth > 0) or (queue_depth > 500):
                        local_faults.append(ledger_name)
            
            # Evaluate systemic health parameters
            if local_faults:
                self.system_faulted = True
                self.tripped_ledgers = local_faults
                self._trigger_emergency_interlock_shutdown()
            else:
                self.system_faulted = False
                self.tripped_ledgers.clear()
                
            # Run checks at a steady 10Hz cadence (Every 100ms)
            time.sleep(0.1)

    def _trigger_emergency_interlock_shutdown(self):
        """Executed instantly if any critical audit trail logs stall or freeze."""
        print(f"\n[CRITICAL_COMPLIANCE_TRIP] AUDIT PIPELINE CORRUPTED OR FROZEN: {self.tripped_ledgers}")
        print("[WATCHDOG] DISPATCHING HARDWARE SAFE MODE OVERRIDE INSTRUCTIONS.")

    def get_watchdog_diagnostics(self) -> dict:
        """Safe thread-locked interface to pass telemetry flags up to the router or UI."""
        current_time = time.time()
        diagnostics = {}
        
        with self.lock:
            for name, last_write in self.ledger_heartbeats.items():
                diagnostics[f"seconds_since_{name.lower()}_write"] = round(current_time - last_write, 3)
                diagnostics[f"queue_depth_{name.lower()}"] = self.ledger_queue_depths[name]
                
        diagnostics['watchdog_system_faulted'] = self.system_faulted
        diagnostics['watchdog_tripped_ledgers'] = self.tripped_ledgers
        return diagnostics

    def start_watchdog(self):
        """Spins up the isolated software-defined tracking inspector thread."""
        if self.is_monitoring:
            return
        self.is_monitoring = True
        
        # Pre-seed heartbeats to current boot time to prevent false triggers during startup
        with self.lock:
            boot_now = time.time()
            for key in self.ledger_heartbeats.keys():
                self.ledger_heartbeats[key] = boot_now
                self.ledger_queue_depths[key] = 0
                
        self.monitor_thread = threading.Thread(target=self._execute_integrity_checker_loop, daemon=True)
        self.monitor_thread.start()

    def stop_watchdog(self):
        """Gracefully secures the monitoring thread context."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print("[WATCHDOG] Compliance watchdog safely secured.")

# Local Verification Run Profile
if __name__ == "__main__":
    wd = MultiLedgerHardwareWatchdog(write_timeout_sec=0.5)
    wd.start_watchdog()
    
    # Simulate a healthy write cycle on your logs
    wd.log_write_success('FLAG_HALYARD_AUDIT', active_queue_size=0)
    wd.log_write_success('MARPOL_BILGE_AUDIT', active_queue_size=0)
    wd.log_write_success('MISSION_TELEMETRY', active_queue_size=0)
    
    print("Simulating an unlogged state failure (simulating a 0.7s file write block with data in queue)...")
    with wd.lock:
        wd.ledger_queue_depths['FLAG_HALYARD_AUDIT'] = 12 # Data is backed up in memory
    time.sleep(0.7)
    
    stats = wd.get_watchdog_diagnostics()
    print(f"Watchdog Fault Active:   {stats['watchdog_system_faulted']}")
    print(f"Tripped Audit Pipelines: {stats['watchdog_tripped_ledgers']}")
    
    wd.stop_watchdog()
