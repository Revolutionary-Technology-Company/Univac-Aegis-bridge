# File Name: shore_audit_logger.py
# Location: /src/network_layer/
# Subsystem: Asynchronous Cryptographically Chained Shore Facility Audit Logger

import os
import csv
import json
import queue
import threading
import time
import hashlib
from typing import Dict, Any

class ShoreFacilityAuditLogger:
    def __init__(self, log_directory: str = "logs", file_prefix: str = "shore_facility_audit"):
        """
        Initializes the thread-isolated asynchronous shore facility log engine.
        Outputs a cryptographically chained CSV ledger and a live state JSON snapshot.
        """
        self.log_dir = os.path.join(os.path.dirname(__file__), "..", log_directory)
        self.file_prefix = file_prefix
        self.csv_file_path = ""
        self.json_file_path = ""
        
        # High-speed RAM thread-safe FIFO buffer queue to offload I/O delays
        self.log_queue = queue.Queue(maxsize=1000)
        self.is_logging = False
        self.worker_thread = None
        
        # Base anchor hash code for the cryptographic verification blockchain pattern
        self.previous_row_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        # Definitive structural header schema mapping for shore facility compliance audits
        self.csv_headers = [
            "timestamp_epoch", "authority_mode", "crane_power_pct", 
            "crane_hook_locked", "blast_door_state", "breaker_relay_state", 
            "sump_pump_state", "hvac_humidity_setpoint", "heating_valve_open",
            "current_row_sha256", "previous_row_sha256"
        ]

    def _initialize_storage_paths(self):
        """Creates the directory matrix and structures the CSV and JSON file endpoints on disk."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
            
        time_str = time.strftime("%Y%m%d")
        
        # Set up path strings
        self.csv_file_path = os.path.join(self.log_dir, f"{self.file_prefix}_{time_str}.csv")
        self.json_file_path = os.path.join(self.log_dir, "shore_facility_live_state.json")
        
        # Write column headers to storage immediately if it is a new file
        if not os.path.exists(self.csv_file_path):
            try:
                with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.csv_headers)
                print(f"[LOGGER] Shore facility compliance ledger deployed at: {self.csv_file_path}")
            except IOError as e:
                print(f"[LOGGER_ERROR] Storage directory write restriction caught during boot: {e}")

    def capture_facility_state_snapshot(self, resolved_facility_states: Dict[str, Any]):
        """
        Non-blocking high-speed RAM entry point. Call this directly inside your 50Hz 
        main calculation loop to cache snapshots cleanly into memory buffers.
        """
        if not self.is_logging:
            return
            
        try:
            act_map = resolved_facility_states.get('dispatched_actuator_cache', {})
            
            # Flatten metrics into a clean intermediate dictionary data block
            snapshot_data = {
                'timestamp': time.time(),
                'mode': resolved_facility_states.get('active_authority_mode', 'UNKNOWN'),
                'crane_pwr': act_map.get('crane_hoist_power_pct', 0.0),
                'hook_locked': act_map.get('crane_hook_lock_solenoid', 1),
                'door_state': act_map.get('blast_door_actuator_state', 0),
                'breaker_state': act_map.get('substation_breaker_relay', 1),
                'sump_state': act_map.get('sump_pump_override_relay', 0),
                'hvac_humidity': act_map.get('hvac_dehumidifier_setpoint', 45.0),
                'heat_valve': act_map.get('climate_heating_valve_open', 0)
            }
            
            # Non-blocking enqueue. If full, drop frame to prioritize calculation clock stability.
            self.log_queue.put_nowait(snapshot_data)
        except queue.Full:
            pass

    def _io_writer_worker_loop(self):
        """Asynchronous disk I/O worker thread loop handling CSV parsing and JSON block updates."""
        self._initialize_storage_paths()
        
        while self.is_logging or not self.log_queue.empty():
            try:
                # Retrieve the snapshot data out of the RAM queue
                data = self.log_queue.get(timeout=1.0)
                
                # --- 1. TAMPER-PROOF CSV CRYPTOGRAPHIC CHAIN GENERATION ---
                # Build a raw string concatenation baseline summarizing the transaction parameters
                metrics_string = f"{data['timestamp']},{data['mode']},{data['crane_pwr']},{data['hook_locked']},{data['door_state']},{data['breaker_state']},{data['sump_state']},{data['hvac_humidity']},{data['heat_valve']}"
                data_string = f"{metrics_string},{self.previous_row_hash}"
                
                # Compute SHA-256 validation hash signature
                current_sha256 = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
                
                # Compile standard flat list mapping row elements matching CSV headers
                final_csv_row = [
                    data['timestamp'], data['mode'], data['crane_pwr'],
                    data['hook_locked'], data['door_state'], data['breaker_state'],
                    data['sump_state'], data['hvac_humidity'], data['heat_valve'],
                    current_sha256, self.previous_row_hash
                ]
                
                # Append line to historical CSV storage file on the disk array
                with open(self.csv_file_path, mode='a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(final_csv_row)
                    
                # Cache current signature hash deep into memory to link the next line
                self.previous_row_hash = current_sha256
                
                # --- 2. LIVE STATE JSON OVERWRITE INTERFACE ---
                # Construct clean external telemetry map payload including active hash links
                json_payload = {
                    "last_updated_epoch": data['timestamp'],
                    "active_authority_mode": data['mode'],
                    "actuator_telemetry": {
                        "crane_hoist_power_pct": data['crane_pwr'],
                        "crane_hook_lock_solenoid": data['hook_locked'],
                        "blast_door_actuator_state": data['door_state'],
                        "substation_breaker_relay": data['breaker_state'],
                        "sump_pump_override_relay": data['sump_state'],
                        "hvac_dehumidifier_setpoint": data['hvac_humidity'],
                        "climate_heating_valve_open": data['heat_valve']
                    },
                    "security_cryptography": {
                        "current_row_sha256": current_sha256,
                        "previous_row_sha256": final_csv_row[-1]
                    }
                }
                
                # Perform atomic overwrite write to json endpoint file
                with open(self.json_file_path, mode='w', encoding='utf-8') as json_f:
                    json.dump(json_payload, json_f, indent=4)
                    
                self.log_queue.task_done()
                
            except queue.Empty:
                continue
            except IOError as disk_fault:
                print(f"[LOGGER_ERROR] Shore facility log disk write delayed: {disk_fault}")
                time.sleep(1.0)

    def start_logger_services(self):
        """Spins up the isolated data-writing worker background thread context."""
        if self.is_logging:
            return
        self.is_logging = True
        self.worker_thread = threading.Thread(target=self._io_writer_worker_loop, daemon=True)
        self.worker_thread.start()
        print("[LOGGER] Asynchronous shore facility audit recording thread active.")

    def stop_logger_services(self):
        """Gracefully flushes remaining data rows to storage and secures file locks."""
        print(f"[LOGGER] Flushing {self.log_queue.qsize()} pending facility logs to storage arrays...")
        self.is_logging = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        print("[LOGGER] Shore facility compliance files closed and secured on hardware storage.")

# Verification and Diagnostic Validation Run Profile
if __name__ == "__main__":
    logger = ShoreFacilityAuditLogger(log_directory="test_logs")
    logger.start_logger_services()
    
    # Generate mock status choices matching a crane hoist event
    mock_resolved_state = {
        'active_authority_mode': 'NETWORK_OVERRIDE',
        'dispatched_actuator_cache': {
            'crane_hoist_power_pct': 75.5,
            'crane_hook_lock_solenoid': 1,
            'blast_door_actuator_state': 0,
            'substation_breaker_relay': 1,
            'sump_pump_override_relay': 1,
            'hvac_dehumidifier_setpoint': 40.0,
            'climate_heating_valve_open': 1
        }
    }
    
    print("\nCaching facility snapshot state parameters into RAM queue arrays...")
    logger.capture_facility_state_snapshot(mock_resolved_state)
    
    time.sleep(0.5) # Let background threads finish writing to files
    logger.stop_logging_services()
    
    # Display the outputs generated to verify compliance formatting
    if os.path.exists(logger.json_file_path):
        with open(logger.json_file_path, 'r') as j_file:
            print("\nGENERATED LIVE SNAPSHOT DATA (JSON SCHEME FORMAT):")
            print("=" * 65)
            print(j_file.read())
            
    # Cleanup verification test files safely
    if os.path.exists(logger.csv_file_path): os.remove(logger.csv_file_path)
    if os.path.exists(logger.json_file_path): os.remove(logger.json_file_path)
    if os.path.exists(logger.log_dir): os.rmdir(logger.log_dir)

    ### 3. Master Orchestration Integration Layer (`main.py`)

    To wire this simultaneous CSV and JSON facility logger straight into your core tracking loops, place the configuration lines directly into **`main.py`**:

    #### Step A: Configure Component Initialization
    At the top of your `bootstrap_system()` function in `main.py`, instantiate and start the shore logging service:

    from network_layer.shore_audit_logger import ShoreFacilityAuditLogger

    # Bootstrap asynchronous shore compliance log tracking
    shore_logger = ShoreFacilityAuditLogger(log_directory="logs", file_prefix="shore_facility_audit")
    shore_logger.start_logger_services()
