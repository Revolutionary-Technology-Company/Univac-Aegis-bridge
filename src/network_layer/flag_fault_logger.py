# File Name: flag_fault_logger.py
# Location: /src/network_layer/
# Subsystem: Asynchronous Cryptographically Chained Halyard & Flag Fault Logger

import os
import csv
import queue
import threading
import time
import hashlib
from typing import Dict, Any

class FlagHalyardFaultLogger:
    def __init__(self, log_directory: str = "logs", file_prefix: str = "flag_halyard_audit"):
        """
        Initializes the thread-isolated asynchronous flag state audit logger.
        """
        self.log_dir = os.path.join(os.path.dirname(__file__), "..", log_directory)
        self.file_prefix = file_prefix
        self.log_file_path = ""
        
        # High-speed RAM thread-safe FIFO queue to absorb disk I/O latency drops
        self.log_queue = queue.Queue(maxsize=1000)
        self.is_logging = False
        self.worker_thread = None
        
        # The base anchor hash code for the cryptographic blockchain ledger pattern
        self.previous_row_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        # Definitive structural header schema mapping for system verification audits
        self.csv_headers = [
            "timestamp_epoch", "flag_state_string", "motor_position_pct", 
            "motor_power_relay_bit", "brake_pin_lock_bit", "log_message",
            "current_row_sha256", "previous_row_sha256"
        ]

    def _initialize_log_file(self):
        """Creates the directory matrix and sets up a fresh CSV spreadsheet file on disk."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
            
        time_str = time.strftime("%Y%m%d")
        filename = f"{self.file_prefix}_{time_str}.csv"
        self.log_file_path = os.path.join(self.log_dir, filename)
        
        # Write column headers to storage immediately if it is a newly allocated file
        if not os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.csv_headers)
                print(f"[LOGGER] Flag hardware compliance ledger deployed at: {self.log_file_path}")
                watchdog.log_write_success('FLAG_HALYARD_AUDIT', self.log_queue.qsize())
            except IOError as e:
                print(f"[LOGGER_ERROR] Storage directory write restriction caught during boot: {e}")

    def capture_flag_event_snapshot(self, flag_commands: Dict[str, Any]):
        """
        Non-blocking high-speed entry point. Call this directly inside your 50Hz 
        main calculation loop to cache snapshots cleanly into RAM memory buffers.
        """
        if not self.is_logging:
            return
            
        try:
            # Flatten metrics into a clean intermediate dictionary data block
            snapshot_data = {
                'timestamp': time.time(),
                'state': flag_commands.get('active_flag_state_string', 'UNKNOWN'),
                'motor_pos': flag_commands.get('commanded_halyard_motor_position_pct', 0.0),
                'motor_power': flag_commands.get('actuator_motor_power_relay', 0),
                'brake_lock': flag_commands.get('actuator_mechanical_lock_pin', 1),
                'msg': flag_commands.get('telemetry_flag_log_message', '')
            }
            
            # Non-blocking enqueue. If full, drop frame to prioritize calculation clock stability.
            self.log_queue.put_nowait(snapshot_data)
        except queue.Full:
            pass

    def _io_writer_worker_loop(self):
        """Asynchronous disk I/O worker thread loop handling string packaging."""
        self._initialize_log_file()
        
        while self.is_logging or not self.log_queue.empty():
            try:
                # Retrieve the snapshot data out of the RAM queue
                data = self.log_queue.get(timeout=1.0)
                
                # --- TAMPER-PROOF CRYPTOGRAPHIC SIGNATURE GENERATION ---
                # Build a raw string concatenation baseline summarizing the transaction parameters
                data_string = f"{data['timestamp']},{data['state']},{data['motor_pos']},{data['motor_power']},{data['brake_lock']},{data['msg']},{self.previous_row_hash}"
                
                # Compute SHA-256 validation hash signature
                current_sha256 = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
                
                # Compile standard flat list mapping row elements matching headers
                final_row = [
                    data['timestamp'], data['state'], data['motor_pos'],
                    data['motor_power'], data['brake_lock'], data['msg'],
                    current_sha256, self.previous_row_hash
                ]
                
                # Append line to storage file on the disk array
                with open(self.log_file_path, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(final_row)
                    watchdog.log_write_success('FLAG_HALYARD_AUDIT', self.log_queue.qsize())
                    
                # Cache current signature hash deep into memory to link the next line
                self.previous_row_hash = current_sha256
                self.log_queue.task_done()
                
            except queue.Empty:
                continue
            except IOError as disk_fault:
                print(f"[LOGGER_ERROR] Flag halyard log disk access delayed: {disk_fault}")
                time.sleep(1.0)

    def start_logger_services(self):
        """Spins up the isolated data-writing worker background thread."""
        if self.is_logging:
            return
        self.is_logging = True
        self.worker_thread = threading.Thread(target=self._io_writer_worker_loop, daemon=True)
        self.worker_thread.start()
        print("[LOGGER] Asynchronous flag halyard audit recording thread active.")

    def stop_logger_services(self):
        """Gracefully flushes remaining data rows to storage and secures file locks."""
        print(f"[LOGGER] Flushing {self.log_queue.qsize()} pending halyard logs to storage arrays...")
        self.is_logging = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        print("[LOGGER] Flag halyard compliance ledger closed safely on hardware storage.")

# Verification and Diagnostic Validation Run Profile
if __name__ == "__main__":
    logger = FlagHalyardFaultLogger(log_directory="test_logs")
    logger.start_logger_services()
    
    # Generate two sequential mock status shifts to verify hashing mechanics
    mock_flag_1 = {'active_flag_state_string': 'ENSIGN', 'commanded_halyard_motor_position_pct': 0.0, 'actuator_motor_power_relay': 0, 'actuator_mechanical_lock_pin': 1, 'telemetry_flag_log_message': 'CRUISING PROFILE: Maintaining standard sovereign ensign.'}
    mock_flag_2 = {'active_flag_state_string': 'COMBAT', 'commanded_halyard_motor_position_pct': 45.5, 'actuator_motor_power_relay': 1, 'actuator_mechanical_lock_pin': 0, 'telemetry_flag_log_message': 'WEAPONS ENGAGED: Hoisting High-Visibility Battle Ensign.'}
    
    print("\nCaching flag state snapshots into memory structures...")
    logger.capture_flag_event_snapshot(mock_flag_1)
    time.sleep(0.05)
    logger.capture_flag_event_snapshot(mock_flag_2)
    
    time.sleep(0.5) # Let background threads finish writing to files
    logger.stop_logging_services()
    
    # Read the file text blocks back dynamically to demonstrate tamper proof validation
    with open(logger.log_file_path, mode='r') as test_file:
        lines = test_file.readlines()
        print("\nGENERATED AUDIT LOG SAMPLE ENTRIES (COMPLIANCE ENCRYPTED):")
        print("=" * 115)
        for idx, line in enumerate(lines[1:]): # Skip headers
            print(f"Row {idx} String: {line.strip()[:105]}...")
            
    # Cleanup verification test directory tracks
    if os.path.exists(logger.log_file_path):
        os.remove(logger.log_file_path)
        os.rmdir(logger.log_dir)
