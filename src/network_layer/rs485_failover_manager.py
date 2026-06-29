#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Advanced RS-485 Failover & Telemetry Exposer
Manages automated hardware switching between primary (A) and backup (B) links,
while tracking sub-millisecond bus latencies for the live JSON matrix stream.
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Tuple
from modbus_framing_engine import ModbusRTUFramingEngine

logger = logging.getLogger("FailoverManager")

class RS485FailoverTelemetryManager:
    def __init__(self, primary_driver, backup_driver, slave_address: int = 0x05, max_retries: int = 3, timeout_seconds: float = 0.150):
        """
        :param primary_driver: The serial bridge node configured for Transceiver Line A.
        :param backup_driver: The secondary serial bridge node configured for Transceiver Line B.
        """
        self.drivers = {
            "LINE_A_PRIMARY": primary_driver,
            "LINE_B_BACKUP": backup_driver
        }
        self.active_line = "LINE_A_PRIMARY"
        
        self.slave_address = slave_address
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.modbus_encoder = ModbusRTUFramingEngine(slave_address=slave_address)
        
        # Microsecond Metrics Metrics Accumulators
        self.last_latency_ms = 0.0
        self.consecutive_failures = 0
        self.total_failovers_tripped = 0
        self.active_alerts = []

    def toggle_hardware_line_relay(self) -> str:
        """
        Physical line matrix transfer pass. Automatically swaps lines when boundaries are breached.
        """
        self.total_failovers_tripped += 1
        if self.active_line == "LINE_A_PRIMARY":
            self.active_line = "LINE_B_BACKUP"
            self.active_alerts.append("LINE_A_TIMEOUT_CRITICAL_FAILOVER_DEPLOYED")
        else:
            self.active_line = "LINE_A_PRIMARY"
            self.active_alerts.append("LINE_B_TIMEOUT_CRITICAL_FAILOVER_DEPLOYED")
            
        logger.critical(f"⚠️ !!! [HARDWARE LINE FAILOVER] !!! Redirecting communication loops to: {self.active_line}")
        return self.active_line

    async def execute_monitored_transaction(self, raw_actuator_mask: int) -> Tuple[bool, str]:
        """
        Asynchronously executes full-duplex writes with timing analysis.
        Automatically trips a line matrix transfer if execution cycles fall below parameters.
        """
        attempt = 0
        current_delay = 0.005
        t_start = time.perf_counter()
        success = False
        
        # Clear transient single-cycle alerts, leaving structural flags active
        self.active_alerts = [a for a in self.active_alerts if "TIMEOUT" not in a]

        while attempt < self.max_retries:
            attempt += 1
            driver = self.drivers[self.active_line]
            try:
                loop = asyncio.get_event_loop()
                # Run the driver write safely inside a non-blocking execution thread context
                await asyncio.wait_for(
                    loop.run_in_executor(None, driver.transmit_modbus_packet_rtu, raw_actuator_mask),
                    timeout=self.timeout_seconds
                )
                success = True
                self.consecutive_failures = 0
                break
                # Insert this check line directly inside the success handling pass of execute_monitored_transaction:
if success:
    # Notify the concurrent watchdog which line cleared the frame successfully
    if hasattr(driver, 'watchdog') and driver.watchdog:
        driver.watchdog.register_line_packet_clear(self.active_line)

                
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Line execution fault on {self.active_line} [Attempt {attempt}]: {str(e)}")
                if attempt == self.max_retries:
                    self.consecutive_failures += 1
                    self.active_alerts.append(f"{self.active_line}_TRANSMISSION_EXHAUSTED")
                await asyncio.sleep(current_delay)
                current_delay *= 2.0

        # Measure precise duration delta in milliseconds
        t_end = time.perf_counter()
        self.last_latency_ms = (t_end - t_start) * 1000.0

        # Trigger Failover Check: Swap paths if the current line drops consecutive cycles
        if not success and self.consecutive_failures >= 1:
            self.toggle_hardware_line_relay()
            
        # Compile complete system matrix state output package
        json_packet = self.compile_telemetry_matrix_packet(raw_actuator_mask, success)
        return success, json_packet

    def compile_telemetry_matrix_packet(self, current_mask: int, last_status_ok: bool) -> str:
        """
        Pipes processing metrics straight into the packed 5x-stacked 36-bit JSON layout matrix.
        """
        current_time = time.time()
        dummy_encoder = self.drivers[self.active_line].modbus_encoder
        
        # Convert performance metrics into clean normalized floating indices [0.0, 1.0]
        clamped_latency_metric = min(1.0, self.last_latency_ms / (self.timeout_seconds * 1000.0 * self.max_retries))
        
        # Build 36-bit hex words tracking infrastructure metrics
        packed_hex_matrix = [
            f"0x{int((1.0 if last_status_ok else 0.0) * 68719476735):010X}", # Word 0: Line Health Vector
            f"0x{int(clamped_latency_metric * 68719476735):010X}",          # Word 1: Normalized Line Latency
            f"0x{current_mask:010X}",                                        # Word 2: Active Outbound Actuator Bits
            f"0x{self.total_failovers_tripped & 0xFFFFFFFF:010X}",           # Word 3: Cumulative Failover Steps
            "0x0000000000"                                                   # Word 4: Reserved System Base Alignment
        ]

        packet = {
            "protocol": "UNIVAC-MATRIX-STREAM",
            "version": "9.2.0-TACTICAL-FAILOVER",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(current_time)),
            "facilityZone": "BUNKER_NETWORK_BACKBONE",
            "matrixState": {
                "stackedWords36": packed_hex_matrix,
                "filterConfidence": 0.9984 if last_status_ok else 0.2105,
                "integrityCheck": "STABLE" if (last_status_ok and self.consecutive_failures == 0) else "DEGRADED"
            },
            "busDiagnostics": {
                "activeTransceiverLine": self.active_line,
                "measuredLoopLatencyMs": float(round(self.last_latency_ms, 3)),
                "consecutiveLineDrops": self.consecutive_failures,
                "triggeredAlertsLog": self.active_alerts
            },
            "routingControls": {
                "isolationGates": "LOCKED" if not last_status_ok else "OPEN",
                "hvacFlowMode": "EXHAUST_ISOLATE" if self.active_line == "LINE_B_BACKUP" else "NORMAL",
                "elevatorBrakes": "MONITORING"
            }
        }
        return json.dumps(packet, indent=2)
