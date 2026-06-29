import { UnivacFramework, NodeTier } from './univac-framework.js';

const systemHub = new UnivacFramework();

// Setup foundational logging handlers
systemHub.on('nodeRegistered', (evt) => {
  console.log(`[SYS LOG] Node online -> ID: ${evt.id} | Tier: ${evt.tier} | Zone: ${evt.zone}`);
});

systemHub.on('auditLog', (log) => {
  console.log(`[AUDIT IMMUTABLE] [${log.timestamp}] Op: ${log.operation} on Node: ${log.nodeId} [Zone: ${log.zone}] by User: ${log.operator}`);
});

systemHub.on('securityAlert', (alert) => {
  console.error(`!!! [SECURITY EMERGENCY ALERT] Type: ${alert.type} | Node: ${alert.nodeId} !!!`);
});

// Run deployment simulation
(async () => {
  console.log('--- INITIALIZING UNIVAC INTEGRATION ENVIRONMENT ---\n');

  // 1. Register a standard third-party hardware relay (e.g., badge reader vendor node)
  systemHub.registerNode({
    id: 'VND-CARD-RDR-04',
    name: 'Acme Perimeter Access Keypad',
    tier: NodeTier.THIRD_PARTY,
    zone: 'PARKING_STRUCTURE_1',
    operations: ['ACTIVATE_RELAY', 'DISABLE_LOCK']
  });

  // 2. Register a Premium Security Node (e.g., primary environmental air locks & containment barriers)
  // Generating a simple certificate stub to satisfy framework validation rules
  const premiumId = 'PREM-HVAC-ISOLATOR-01';
  const validSignature = `VALID_CERT_${premiumId}_KEY_88B3`;

  systemHub.registerNode({
    id: premiumId,
    name: 'Sperry-Aegis High-Pressure HVAC Gate',
    tier: NodeTier.PREMIUM_SECURITY,
    zone: 'ISOLATION_WARD_3',
    operations: ['REVERSE_AIR_FLOW', 'HALT_EXHAUST', 'SEAL_VENTILATION'],
    vendorSignature: validSignature
  });

  // 3. Register a Premium Security Access point for elevator structural containment
  const elevatorNodeId = 'PREM-ELEV-CTRL-22';
  systemHub.registerNode({
    id: elevatorNodeId,
    name: 'Sperry-Aegis Main Shaft Lift Brake',
    tier: NodeTier.PREMIUM_SECURITY,
    zone: 'ISOLATION_WARD_3',
    operations: ['BYPASS_FLOOR', 'LOCK_CAR_AT_GROUND'],
    vendorSignature: `VALID_CERT_${elevatorNodeId}_KEY_77A1`
  });

  console.log('\n--- SYSTEM ARCHITECTURE VERIFIED. EXECUTING TEST PROCEDURES ---');

  // Triggering an isolated containment command example
  try {
    const cmdResult = await systemHub.executeNodeCommand('PREM-HVAC-ISOLATOR-01', 'SEAL_VENTILATION', {
      operatorId: 'SEC_OFFICER_902'
    });
    console.log(`[CMD RESPONSE] Result Status: ${cmdResult.status}\n`);
  } catch (err) {
    console.error(`Command execution failed: ${err.message}`);
  }

  // Performing a bulk system isolation override on a distinct target zone
  console.log('--- INITIATING AUTOMATED BROADCAST OVERRIDE FOR ZONE: ISOLATION_WARD_3 ---');
  // Attempt to lock down matching systems in Ward 3 while letting standard vendor nodes remain untouched
  await systemHub.broadcastZoneOverride('ISOLATION_WARD_3', 'SEAL_VENTILATION', {
    operatorId: 'AUTOMATED_EVAC_DAEMON'
  });

  console.log('\n--- SIMULATION DISPATCH RECORD FINISHED ---');
})();
