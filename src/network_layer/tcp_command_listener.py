#!/usr/bin/env python3
"""
Univac-Aegis-bridge: TCP Command Listener Extension
Receives network commands or raw payload bytes over dedicated network sockets.
"""
# File Name: tcp_command_listener.py
# Location: /src/network_layer/
# Subsystem: Asynchronous TCP Network Target Command Server

import socket
import threading
import json
import time
from typing import Dict, Any
import logging
import socket
from univac_node_matrix_processor import UnivacNodeMatrixProcessor

logger = logging.getLogger("TCPListener")

class TCPCommandMatrixBridge:
    def __init__(self, router_instance=None):
        self.node_processor = UnivacNodeMatrixProcessor(zone_identifier="BUNKER_TCP_NODE")
        self.router = router_instance

    def process_tcp_stream_chunk(self, client_socket: socket.socket) -> None:
        """
        Reads a data chunk from an active TCP connection socket.
        Expects a single byte header representing the relay pin register state.
        """
        try:
            # Read a single hardware status byte from the TCP buffer
            data = client_socket.recv(1)
            if not data:
                return

            pin_register = int(data[0])
            
            # Generate the unified JSON system string
            json_frame = self.node_processor.compile_live_matrix_packet(pin_register)
            
            if self.router:
                self.router.ingest_live_system_frame(json_frame)
                
        except Exception as e:
            logger.error(f"TCP Stream tracking processing anomaly: {str(e)}")

class JsonTcpCommandListener:
    def __init__(self, host_ip: str = "0.0.0.0", port: int = 7000):
        """
        Initializes the TCP network command server.
        host_ip: "0.0.0.0" allows the server to bind to all active network interfaces.
        port: Dedicated port listening for incoming target configuration frames.
        """
        self.host_ip = host_ip
        self.port = port
        
        # Initialize standard socket layer
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.is_running = False
        self.listen_thread = None
        self.active_connections = []
        
        # Safe thread-locked cache storage for ordered setpoints
        self.data_lock = threading.Lock()
        self.target_setpoints = {
            'rpm': 0.0,
            'target_yaw_rate': 0.0
        }

    def validate_and_update_targets(self, json_payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Enforces strict safety parameter checks on values parsed from the network wire 
        before letting them pass into the main propulsion matrices.
        """
        try:
            new_rpm = json_payload.get('rpm')
            new_yaw_rate = json_payload.get('target_yaw_rate')
            
            # 1. Structural validation checks
            if new_rpm is None or new_yaw_rate is None:
                return False, "REJECTED: Missing required key 'rpm' or 'target_yaw_rate'"
                
            # 2. Mathematical physical constraint checks
            # Clamp or reject extreme requested configurations
            if not (-200.0 <= new_rpm <= 1200.0):
                return False, "REJECTED: Requested RPM out of structural design range (-200 to 1200)"
                
            if not (-0.8 <= new_yaw_rate <= 0.8):
                return False, "REJECTED: Requested turning rate exceeds physical rudder capability"
                
            # Update target registers via thread-safe lock operation
            with self.data_lock:
                self.target_setpoints['rpm'] = float(new_rpm)
                self.target_setpoints['target_yaw_rate'] = float(new_yaw_rate)
                
            return True, "ACCEPTED: Targets updated successfully"
            
        except (ValueError, TypeError) as parse_err:
            return False, f"REJECTED: Invalid value type formatting error: {parse_err}"

    def get_latest_targets(self) -> Dict[str, Any]:
        """Thread-safe snapshot interface accessible by the central bridge execution loop."""
        with self.data_lock:
            return self.target_setpoints.copy()

    def _handle_client_stream(self, client_socket: socket.socket, client_address: tuple):
        """Dedicated connection thread handling the socket buffer for an individual connected system."""
        print(f"[TCP] New active terminal link accepted from station: {client_address}")
        client_socket.settimeout(5.0) # Terminate idle streams to preserve bridge memory limits
        
        buffer = ""
        while self.is_running:
            try:
                # Read chunks across the network socket
                data = client_socket.recv(1024)
                if not data:
                    break # Client closed the link stream connection cleanly
                    
                buffer += data.decode('utf-8', errors='ignore')
                
                # Check for standard newline framing delimiters
                if "\n" in buffer:
                    lines = buffer.split("\n")
                    # Save the last item if it's incomplete, process the others
                    buffer = lines[-1]
                    
                    for line in lines[:-1]:
                        if not line.strip():
                            continue
                            
                        try:
                            # Ingest the string packet payload
                            command_packet = json.loads(line)
                            success, response_msg = self.validate_and_update_targets(command_packet)
                            
                            # Transmit immediate verification feedback back over the TCP link
                            status_frame = {"status": "OK" if success else "ERROR", "message": response_msg}
                            client_socket.sendall((json.dumps(status_frame) + "\n").encode('utf-8'))
                            
                        except json.JSONDecodeError:
                            err_frame = {"status": "ERROR", "message": "REJECTED: Malformed JSON syntax"}
                            client_socket.sendall((json.dumps(err_frame) + "\n").encode('utf-8'))
                            
            except socket.timeout:
                continue # Normal keep-alive processing window heartbeat
            except Exception as e:
                print(f"[TCP_ERROR] Terminal disconnect on {client_address}: {e}")
                break
                
        client_socket.close()
        with self.data_lock:
            if client_socket in self.active_connections:
                self.active_connections.remove(client_socket)

    def _server_accept_loop(self):
        """Asynchronous background socket accept execution thread loop."""
        self.server_socket.bind((self.host_ip, self.port))
        self.server_socket.listen(5)
        print(f"[TCP] Core Command Server Listening on network interface ports at {self.host_ip}:{self.port}")
        
        while self.is_running:
            try:
                self.server_socket.settimeout(1.0)
                client_sock, client_addr = self.server_socket.accept()
                
                with self.data_lock:
                    self.active_connections.append(client_sock)
                    
                # Hand over streaming data processing responsibilities to an independent worker thread
                client_handler = threading.Thread(
                    target=self._handle_client_stream, 
                    args=(client_sock, client_addr), 
                    daemon=True
                )
                client_handler.start()
                
            except socket.timeout:
                continue # Recycle the check parameter loop validation gates
            except Exception as e:
                if self.is_running:
                    print(f"[TCP_CRITICAL] Server loop fault: {e}")
                break

    def start_server(self):
        """Spins up the isolated network command parsing server infrastructure thread."""
        if self.is_running:
            return
        self.is_running = True
        self.listen_thread = threading.Thread(target=self._server_accept_loop, daemon=True)
        self.listen_thread.start()

    def stop_server(self):
        """Gracefully closes down network listeners and drops existing client streams."""
        self.is_running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
            
        with self.data_lock:
            for sock in self.active_connections:
                try: sock.close()
                except: pass
            self.active_connections.clear()
            
        try: self.server_socket.close()
        except: pass
        print("[TCP] Network Target Command Server safely offline.")

# Verification Integration Check Environment
if __name__ == "__main__":
    server = JsonTcpCommandListener(host_ip="127.0.0.1", port=7000)
    server.start_server()
    
    # Internal validation emulation test mimicking a network connection transmission
    print("\nExecuting network interface string update validation test...")
    sample_raw_json_frame = {"rpm": 450.0, "target_yaw_rate": 0.05}
    
    is_valid, msg = server.validate_and_update_targets(sample_raw_json_frame)
    print(f"Validation Status Message: {msg}")
    
    current_targets = server.get_latest_targets()
    print(f"Verified Active System Targets State: {current_targets}")
    
    server.stop_server()
