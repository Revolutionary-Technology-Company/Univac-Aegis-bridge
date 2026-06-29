/**
 * Univac-IX: Central Graphical Terminal Dashboard (app_interface.js)
 * Parses incoming live-streaming telemetry matrices and renders active 
 * failover alert logs, bus latencies, and structural security states.
 */

export class CentralTerminalDashboard {
  constructor(containerElementId) {
    this.container = document.getElementById(containerElementId);
    this.initializeLayout();
  }

  /**
   * Builds the foundational HTML skeleton for a high-visibility security grid
   */
  initializeLayout() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div style="background-color: #050505; color: #00FF00; font-family: 'Courier New', monospace; padding: 20px; border: 2px solid #333; border-radius: 5px;">
        <h2 style="text-align: center; color: #00FF00; border-bottom: 1px solid #00FF00; padding-bottom: 10px; margin-top: 0;">
          ⚡ UNIVAC CENTRAL TACTICAL BACKPLANE STATUS PANEL ⚡
        </h2>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
          <!-- Left Column: Core Diagnostics -->
          <div style="border: 1px solid #00FF00; padding: 10px; background-color: #0a0a0a;">
            <h3 style="margin-top: 0; color: #FFF; border-bottom: 1px dashed #00FF00;">BUS DIAGNOSTICS</h3>
            <p>Active Line: <span id="dash-active-line" style="font-weight: bold; color: #FFFF00;">LINE_A_PRIMARY</span></p>
            <p>Loop Latency: <span id="dash-latency">0.000</span> ms</p>
            <p>Consecutive Drops: <span id="dash-drops" style="color: #FF0000;">0</span></p>
            <p>System Integrity: <span id="dash-integrity" style="font-weight: bold;">STABLE</span></p>
          </div>
          
          <!-- Right Column: Environmental Posture -->
          <div style="border: 1px solid #00FF00; padding: 10px; background-color: #0a0a0a;">
            <h3 style="margin-top: 0; color: #FFF; border-bottom: 1px dashed #00FF00;">TACTICAL POSTURE</h3>
            <p>Isolation Gates: <span id="dash-gates" style="font-weight: bold;">OPEN</span></p>
            <p>HVAC Flow Mode: <span id="dash-hvac">NORMAL</span></p>
            <p>Elevator Brakes: <span id="dash-brakes">MONITORING</span></p>
            <p>Last Sync Tock: <span id="dash-timestamp" style="color: #888;">--:--:--</span></p>
          </div>
        </div>

        <!-- Bottom Row: Dynamic Alert Manifest -->
        <div style="margin-top: 20px; border: 1px solid #FF0000; padding: 10px; background-color: #100000;">
          <h3 style="margin-top: 0; color: #FF3333; border-bottom: 1px dashed #FF0000;">🚨 ACTIVE TELEMETRY ALERT LOG</h3>
          <div id="dash-alerts-container" style="max-height: 100px; overflow-y: auto; font-size: 14px; color: #FF5555;">
            <div style="color: #00FF00;">> SYSTEM SCAN RUNNING: NO ACTIVE HARDWARE RE-ROUTE EVENTS DETECTED</div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Ingests a raw JSON telemetry packet string from the network matrix stream 
   * and updates UI coordinate elements instantly.
   * @param {string} rawJsonPacket Streaming network JSON string payload
   */
  updateDashboardView(rawJsonPacket) {
    try {
      const data = JSON.parse(rawJsonPacket);
      if (data.protocol !== "UNIVAC-MATRIX-STREAM") return;

      const diagnostics = data.busDiagnostics || {};
      const matrixState = data.matrixState || {};
      const controls = data.routingControls || {};

      // 1. Refresh Bus Diagnostics Text Layers
      document.getElementById("dash-active-line").innerText = diagnostics.activeTransceiverLine || "UNKNOWN";
      document.getElementById("dash-latency").innerText = diagnostics.measuredLoopLatencyMs !== undefined ? diagnostics.measuredLoopLatencyMs.toFixed(3) : "0.000";
      
      const dropCounter = document.getElementById("dash-drops");
      dropCounter.innerText = diagnostics.consecutiveLineDrops || 0;
      dropCounter.style.color = (diagnostics.consecutiveLineDrops > 0) ? "#FF0000" : "#00FF00";

      const integrityField = document.getElementById("dash-integrity");
      integrityField.innerText = matrixState.integrityCheck || "UNKNOWN";
      integrityField.style.color = (matrixState.integrityCheck === "STABLE") ? "#00FF00" : "#FF0000";

      // 2. Refresh Automation Control Postures
      const gatesField = document.getElementById("dash-gates");
      gatesField.innerText = controls.isolationGates || "OPEN";
      gatesField.style.color = (controls.isolationGates === "LOCKED") ? "#FF0000" : "#00FF00";
      
      document.getElementById("dash-hvac").innerText = controls.hvacFlowMode || "NORMAL";
      document.getElementById("dash-brakes").innerText = controls.elevatorBrakes || "MONITORING";
      document.getElementById("dash-timestamp").innerText = data.timestamp ? data.timestamp.split("T")[1].substring(0, 8) : "--:--:--";

      // 3. Populate Active Critical Alerts List
      const alertsContainer = document.getElementById("dash-alerts-container");
      const alertsLog = diagnostics.triggeredAlertsLog || [];

      if (alertsLog.length === 0) {
        alertsContainer.innerHTML = `<div style="color: #00FF00;">> SYSTEM STATUS HEALTHY: NO ACTIVE HARDWARE INTERCEPT CONDITIONS KEYED</div>`;
      } else {
        alertsContainer.innerHTML = alertsLog.map(alert => `
          <div style="margin-bottom: 4px; font-weight: bold; border-left: 3px solid #FF0000; padding-left: 5px;">
            ⚠️ [CRITICAL ALERT] -> ${alert}
          </div>
        `).join("");
      }

    } catch (err) {
      console.error("[DASHBOARD PARSE EXCEPTION] Malformed matrix chunk dropped:", err);
    }
  }
}
