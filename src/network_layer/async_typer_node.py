#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Main Async Typer Network Node
Orchestrates service startup, binds TCP network sockets, and parses 
terminal flags to configure industrial Modbus node tracking addresses.
"""
# File Name: async_typer_node.py
# Location: /src/network_layer/
# Subsystem: Asynchronous Non-Blocking Character Typer Engine
import typer
import asyncio
import logging
import sys
from typing import Optional
import threading
import queue
import time
import tkinter as tk

# System Initialization Blueprint Example
from tcp_command_listener import MultiThreadedTCPListener
from hardware_watchdog import ComprehensiveHardwareWatchdog
from tcp_command_listener import MultiThreadedTCPListener
from bridge_network_router import BridgeNetworkRouterExtension

logging.basicConfig(level=logging.INFO, format='[UNIVAC-SERVICE] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ServiceDaemon")

app = typer.Typer(help="UNIVAC Aegis Bridge Tactical Network Command Center")

# 1. Boot diagnostic security guards first
watchdog = ComprehensiveHardwareWatchdog(target_frequency_hz=4.0)
watchdog.start()

# 2. Bind the primary routing table matrix
router = BridgeNetworkRouterExtension(hardware_watchdog_instance=watchdog)

# 3. Spin up network server binds with live intercepts
tcp_server = MultiThreadedTCPListener(host="0.0.0.0", port=8080, router_instance=router)
tcp_server.start_server()

@app.command()
def start_node_service(
    port: int = typer.Option(8080, "--port", "-p", help="Target TCP listener port bind allocation."),
    slave_id: int = typer.Option(0x05, "--slave-id", "-s", help="Modbus RTU target hardware slave identifier on RS-485 bus."),
    baudrate: int = typer.Option(9600, "--baudrate", "-b", help="Serial connection baud rate speed (e.g., 9600, 19200, 115200).")
):
    """
    Initializes the network node runtime lifecycle with customizable line speed and addressing flags.
    """
    logger.info("Initializing UNIVAC Aegis Bridge subsystem cluster...")
    
    if slave_id < 1 or slave_id > 247:
        logger.critical(f"❌ [CONFIGURATION ERROR] Invalid Modbus address: {slave_id}. Limit must match [1-247].")
        sys.exit(1)

    # Standard commercial serial line-speed validation check
    valid_baudrates = {1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200}
    if baudrate not in valid_baudrates:
        logger.critical(f"❌ [CONFIGURATION ERROR] Unsupported line speed: {baudrate} bps. Use standard values.")
        sys.exit(1)

    logger.info(f"Target Configuration -> Slave Station ID: 0x{slave_id:02X} | Bus Line Speed: {baudrate} bps")

    try:
        # 1. Boot structural tracking diagnostics
        watchdog = ComprehensiveHardwareWatchdog(target_frequency_hz=4.0)
        watchdog.start()

        # 2. Bind the primary telemetry routing table with configuration variables
        router = BridgeNetworkRouterExtension(hardware_watchdog_instance=watchdog)
        router.target_modbus_slave_address = slave_id
        router.configured_bus_baudrate = baudrate

        # 3. Spin up multi-threaded network server binders
        tcp_server = MultiThreadedTCPListener(host="0.0.0.0", port=port, router_instance=router)
        tcp_server.start_server()
        
        logger.info(f"🎉 System initialization complete. Network operational via port {port}.")
        
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        logger.warning("\nSystem shutdown sequence tripped by keyboard intercept signal.")
    except Exception as e:
        logger.critical(f"Unhandled fatal runtime failure: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    app()
    
@app.command()
def start_node_service(
    port: int = typer.Option(8080, "--port", "-p", help="Target TCP listener port bind allocation."),
    slave_id: int = typer.Option(0x05, "--slave-id", "-s", help="Modbus RTU target hardware slave identifier on RS-485 bus.")
    baudrate: int = typer.Option(9600, "--baudrate", "-b", help="Serial connection baud rate speed (e.g., 9600, 19200, 115200).")
):
    """
    Initializes the network node runtime lifecycle. Sets up diagnostics,
    routes tracking tables, and binds communication sockets.
    """
    logger.info("Initializing UNIVAC Aegis Bridge subsystem cluster...")
    
    # Range validation for Modbus node IDs (1 to 247 are valid slave addresses)
    if slave_id < 1 or slave_id > 247:
        logger.critical(f"❌ [CONFIGURATION ERROR] Invalid Modbus address: {slave_id}. Limit must match [1-247].")
        sys.exit(1)

    logger.info(f"Target multi-drop slave station address assigned: 0x{slave_id:02X}")

    try:
        # 1. Boot structural tracking diagnostics
        watchdog = ComprehensiveHardwareWatchdog(target_frequency_hz=4.0)
        watchdog.start()
        logger.info("✅ Comprehensive hardware monitoring watchdog online.")

        # 2. Bind the primary telemetry routing table
        router = BridgeNetworkRouterExtension(hardware_watchdog_instance=watchdog)
        router.configured_bus_baudrate = baudrate

        # Pass runtime station ID allocations directly into sub-processing contexts
        router.target_modbus_slave_address = slave_id

        # 3. Spin up multi-threaded network server binders
        tcp_server = MultiThreadedTCPListener(host="0.0.0.0", port=port, router_instance=router)
        tcp_server.start_server()
        
        logger.info(f"🎉 System initialization complete. Network operational via port {port}.")
        
        # Keep execution loops parsing asynchronously
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        logger.warning("\nSystem shutdown sequence tripped by keyboard intercept signal.")
    except Exception as e:
        logger.critical(f"Unhandled fatal runtime failure inside service container: {str(e)}")
        sys.exit(1)
if __name__ == "__main__":
    app()

class AsyncTyperNode:
    def __init__(self, target_text_widget: tk.Text, character_delay_sec: float = 0.01):
        """
        Initializes the asynchronous string typing processor.
        target_text_widget: The Tkinter Text box UI component to write to.
        character_delay_sec: Time delay between individual typed characters.
        """
        self.widget = target_text_widget
        self.delay = character_delay_sec
        self.input_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None

    def queue_text_block_overwrite(self, text_string: str):
        """Safe thread-locked entry point. Drops complete text frames into the queue."""
        self.input_queue.put(text_string)

    def _typer_worker_loop(self):
        """Asynchronous character streaming thread loop."""
        while self.is_running:
            try:
                # Block until a new text block frame arrives
                text_block = self.input_queue.get(timeout=1.0)
                
                # Clear target text widget via a safe main UI thread call
                self.widget.after(0, lambda: self.widget.delete("1.0", tk.END))
                
                # Stream characters sequentially to create an industrial printout effect
                for char in text_block:
                    if not self.is_running:
                        break
                    # Append character to widget safely on the main thread execution line
                    self.widget.after(0, lambda c=char: self.widget.insert(tk.END, c))
                    self.widget.after(0, lambda: self.widget.see(tk.END))
                    time.sleep(self.delay)
                    
                self.input_queue.task_done()
            except queue.Empty:
                continue

    def start_typer(self):
        """Spins up the isolated character writing thread context."""
        if self.is_running:
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._typer_worker_loop, daemon=True)
        self.worker_thread.start()

    def stop_typer(self):
        """Safely shuts down the typer thread loop."""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
