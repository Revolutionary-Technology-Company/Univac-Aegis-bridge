#!/usr/bin/env python3
"""
Univac-Aegis-bridge: Asynchronous RS-485 Request-Response Manager
Implements timeout mechanics and back-off retries for uncommunicative slave devices.
"""

import asyncio
import logging

logger = logging.getLogger("RetryManager")

class AsyncRS485RetryManager:
    def __init__(self, serial_interface_wrapper, max_retries: int = 3, timeout_seconds: float = 0.150):
        """
        :param serial_interface_wrapper: Instance of your full-duplex serial driver node.
        :param max_retries: Total allowed re-transmission attempts per command block.
        :param timeout_seconds: Maximum duration to wait for slave response echo lines.
        """
        self.driver = serial_interface_wrapper
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    async def execute_transaction_with_retry(self, raw_actuator_mask: int) -> bool:
        """
        Asynchronously handles an outbound transmission loop.
        Retries up to max_retries if the target slave node experiences bus dropout.
        """
        attempt = 0
        current_delay = 0.010  # Baseline 10ms exponential back-off start delay

        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.debug(f"Dispatching Modbus frame to bus. Attempt {attempt} of {self.max_retries}...")
                
                # Run the synchronous driver write operation in a non-blocking thread pool executor
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, self.driver.transmit_modbus_packet_rtu, raw_actuator_mask),
                    timeout=self.timeout_seconds
                )
                
                # Check line echo or acknowledgment tracking metrics (Simulated here)
                # If the line clears without physical faults, return true instantly
                logger.info(f"✅ Transaction completed successfully on attempt {attempt}.")
                return True

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ [TIMEOUT FAULT] Slave failed to acknowledge frame within {self.timeout_seconds}s on attempt {attempt}.")
            except Exception as e:
                logger.error(f"⚠️ [BUS ERROR] Transient physical error encountered on attempt {attempt}: {str(e)}")

            # Enforce back-off sleep delay before attempting execution retry
            if attempt < self.max_retries:
                await asyncio.sleep(current_delay)
                current_delay *= 2.0  # Double delay curve to clear bus congestion

        logger.critical(f"❌ [SLAVE NODE UNRESPONSIVE] Max retries ({self.max_retries}) exhausted. Dropping communication loop.")
        return False
