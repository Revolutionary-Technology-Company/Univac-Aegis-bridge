// Saved as aegis_kinematics.hpp
#pragma once
#include <cmath>

struct EcefCoordinates {
    double x; // Meters
    double y; // Meters
    double z; // Meters
};

// Converts raw 1970s radar inputs into absolute global 3D space
EcefCoordinates translate_legacy_to_ecef(uint32_t range_yds, uint32_t bearing_min, uint32_t alt_ft, 
                                         double ship_lat_rad, double ship_lon_rad, double ship_heading_rad) {
    // 1. Convert imperial inputs to metric standards
    double range_meters = range_yds * 0.9144;
    double altitude_meters = alt_ft * 0.3048;
    // Convert bearing arcminutes to true radians relative to ship centerline
    double relative_bearing_rad = (bearing_min / 60.0) * (M_PI / 180.0); 

    // 2. Resolve true target heading by incorporating the ship's gyrocompass
    double true_bearing_rad = relative_bearing_rad + ship_heading_rad;

    // 3. Simple spherical coordinate mapping to local ENU (East, North, Up) framework
    double east  = range_meters * std::sin(true_bearing_rad);
    double north = range_meters * std::cos(true_bearing_rad);
    double up    = altitude_meters;

    // 4. Transform Local ENU vectors into final ECEF Global Cartesian space
    EcefCoordinates target_pos;
    target_pos.x = -std::sin(ship_lon_rad) * east - std::sin(ship_lat_rad) * std::cos(ship_lon_rad) * north + std::cos(ship_lat_rad) * std::cos(ship_lon_rad) * up;
    target_pos.y =  std::cos(ship_lon_rad) * east - std::sin(ship_lat_rad) * std::sin(ship_lon_rad) * north + std::cos(ship_lat_rad) * std::sin(ship_lon_rad) * up;
    target_pos.z =  std::cos(ship_lat_rad) * north + std::sin(ship_lat_rad) * up;

    return target_pos;
}
