# File Name: async_typer_node.py
# Location: /src/network_layer/
# Subsystem: Asynchronous Non-Blocking Character Typer Engine

import threading
import queue
import time
import tkinter as tk

# System Initialization Blueprint Example
from hardware_watchdog import ComprehensiveHardwareWatchdog
from tcp_command_listener import MultiThreadedTCPListener
from bridge_network_router import BridgeNetworkRouterExtension

# 1. Boot diagnostic security guards first
watchdog = ComprehensiveHardwareWatchdog(target_frequency_hz=4.0)
watchdog.start()

# 2. Bind the primary routing table matrix
router = BridgeNetworkRouterExtension(hardware_watchdog_instance=watchdog)

# 3. Spin up network server binds with live intercepts
tcp_server = MultiThreadedTCPListener(host="0.0.0.0", port=8080, router_instance=router)
tcp_server.start_server()

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
