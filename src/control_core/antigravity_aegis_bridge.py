import asyncio
import aiohttp
import uuid
import numpy as np
from datetime import datetime
from numba import njit

@njit(fastmath=True)
def calculate_field_distortion(mass_matrix: np.ndarray, spin_rate: float) -> float:

    """ Numba-optimized FastMath logic replacing slow runtime float division """

    if spin_rate == 0.0:
        return 0.0
    return np.sum(mass_matrix) * (9.81 / spin_rate)

class AntigravityAegisBridge:

    """ Asynchronous bridge for quantum and kinematic telemetry """

    def __init__(self, aegis_url: str):
        self.aegis_url = aegis_url
        self.session = None
        self.node_id = "Antigravity-Drive-Alpha"

    async def initialize(self):
        """ Instantiates the asynchronous HTTP session """
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2.0))

        self.uplink_authorized = False

    async def shutdown(self):

        if not self.session:
            return
        await self.session.close()

    def determine_severity(self, distortion_metric: float) -> tuple:

        """ Severity routing logic matrix """

        if distortion_metric > 15000.0:
            return 9, "CRITICAL_GRAVITY_SHEAR"
        if distortion_metric > 8000.0:
            return 4, "WARN_FIELD_FLUCTUATION"
        return 0, "NOMINAL_FIELD_STATE"

    async def dispatch_telemetry(self, mass_array: np.ndarray, spin_rate: float, power_draw: float):

        if not self.uplink_authorized:
            return

        distortion_metric = calculate_field_distortion(mass_array, spin_rate)
        severity, event_type = self.determine_severity(distortion_metric)

        aegis_payload = {
            "EventId": str(uuid.uuid4()),
            "Timestamp": datetime.utcnow().isoformat() + "Z",
            "SourceNode": self.node_id,
            "EventType": event_type,
            "SeverityLevel": severity,
            "RawProtocolData": str(distortion_metric) + " | " + str(power_draw)
        }

        headers = {"X-Aegis-Client": self.node_id, "Content-Type": "application/json"}
        
        try:
            await self.session.post(self.aegis_url, json=aegis_payload, headers=headers)
        except Exception:
            pass