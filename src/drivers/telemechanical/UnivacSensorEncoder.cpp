// Explicit mapping of Virtual Track Checkpoints to UNIVAC parallel tracking registers
uint32_t serialize_univac_sensor_state(const std::string& active_sensor_id) {
    uint32_t dwUnivacBuffer = 0x00000000;

    if (active_sensor_id == "VS_00_WESTLAKE_GATE")      dwUnivacBuffer |= 0x00000001; // Bit 0: South Platform
    if (active_sensor_id == "VS_01_GAUNTLET_ENTRY")     dwUnivacBuffer |= 0x00000002; // Bit 1: Gauntlet zone
    if (active_sensor_id == "VS_02_STEWART_INTERCEPT")   dwUnivacBuffer |= 0x00000004; // Bit 2: Stewart Turn
    if (active_sensor_id == "VS_03_DENNY_STRAIGHTAWAY") dwUnivacBuffer |= 0x00000008; // Bit 3: High-speed run
    if (active_sensor_id == "VS_04_BATTERY_COAST_ZONE")  dwUnivacBuffer |= 0x00000010; // Bit 4: Coast loop active
    if (active_sensor_id == "VS_05_MOPOP_MUSEUM_INTERSECT") dwUnivacBuffer |= 0x00000020; // Bit 5: MoPOP Curve
    if (active_sensor_id == "VS_06_SEATTLE_CENTER_GATE") dwUnivacBuffer |= 0x00000040; // Bit 6: North Platform

    // Hard-wired safety check: Keep the 100ms system watchdog active
    dwUnivacBuffer |= 0x40000000; 

    return dwUnivacBuffer;
}

