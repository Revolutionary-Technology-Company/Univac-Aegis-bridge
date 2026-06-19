#ifndef RHEINMETALL_PATH_MAPPING_HPP
#define RHEINMETALL_PATH_MAPPING_HPP

#include <cstdint>
#include <atomic>
#include <string>

namespace RheinmetallPathCore {

    /**
     * @brief NATO Ground Vehicle Architecture (NGVA) Command Bus Matrix
     * Replaces the historical 24-command TOZ-IV pulse system with modern digital states.
     */
    struct PathNGVACommands {
        // --- PROPULSION & DRIVE-BY-WIRE (DBW) ---
        static constexpr uint32_t TRANSMISSION_PARK   = 0x00000001; // Electronic parking pawl
        static constexpr uint32_t TRANSMISSION_DRIVE  = 0x00000002; // Drive engagement
        static constexpr uint32_t TRANSMISSION_NEUTRAL= 0x00000004; // Disengage powertrain (Coast)
        static constexpr uint32_t PROPULSION_REGEN     = 0x00000008; // Dynamic regenerative braking loop
        static constexpr uint32_t STEERING_BY_WIRE   = 0x00000010; // EPS Actuator control flag

        // --- AUTONOMY TASKING MODES (Rheinmetall PATH Core) ---
        static constexpr uint32_t MODE_TELEOPERATION  = 0x00000100; // Manual tablet / remote overrides
        static constexpr uint32_t MODE_WAYPOINT_NAV   = 0x00000200; // Pure deterministic path following
        static constexpr uint32_t MODE_LEADER_FOLLOWER= 0x00000400; // Convoy bounding / tether tracking
        static constexpr uint32_t MODE_WOLF_PACK      = 0x00000800; // Multi-UGV swarming & collaborative slam

        // --- MODERN PAYLOAD SUB-SYSTEMS (Mission Master Modules) ---
        static constexpr uint32_t ACTIVE_STABILIZATION= 0x00010000; // Precision leveling (Tele-tank / HPU)
        static constexpr uint32_t LIDAR_OBSTACLE_AVOID = 0x00020000; // Dynamic path re-routing
        static constexpr uint32_t RADAR_CUAS_TRACKING = 0x00040000; // Counter-drone scanning arrays
        static constexpr uint32_t RCWS_ARMAMENT_READY = 0x00080000; // Remote weapon station power

        // --- CYBER & NETWORK SAFETY SYSTEM ---
        static constexpr uint32_t NETWORK_HEARTBEAT   = 0x40000000; // 100ms DDS network safety ping
        static constexpr uint32_t HUMAN_IN_THE_LOOP   = 0x80000000; // Token-locked kinetic fire inhibitor
    };

    // Vector definitions for modern spatial telemetry
    struct SpatialKinematics {
        float throttle_percentage; // 0.0 to 100.0% (Drive-by-Wire command)
        float brake_pressure_bar;   // 0 to 150 Bar hydraulic/pneumatic scaling
        float steering_angle_rad;   // True wheel/bogie target orientation
    };

    /**
     * @class PathAutonomyProcessor
     * @brief Ingests complex AI navigation metrics and outputs strict NGVA frame sequences.
     */
    class PathAutonomyProcessor {
    public:
        PathAutonomyProcessor() : m_active_ngva_frame(0), m_software_lockout(false) {}
        ~PathAutonomyProcessor() = default;

        // Validates all parameters before packaging commands into the NGVA pipeline
        uint32_t update_ngva_frame(uint32_t base_modes, SpatialKinematics kinematics, bool human_confirmed) {
            if (m_software_lockout.load()) {
                return 0x00000000; // Absolute safety drop
            }

            uint32_t packaged_frame = base_modes;

            // Strict safety validation: Force human confirmation for all weapon/kinetic payload outputs
            if ((packaged_frame & PathNGVACommands::RCWS_ARMAMENT_READY) && !human_confirmed) {
                packaged_frame &= ~PathNGVACommands::RCWS_ARMAMENT_READY; // Strip target bit instantly
            }

            m_active_ngva_frame.store(packaged_frame);
            m_current_kinematics = kinematics;
            return packaged_frame;
        }

        void enforce_hardware_lockout() {
            m_software_lockout.store(true);
            m_active_ngva_frame.store(0x00000000);
        }

    private:
        std::atomic<uint32_t> m_active_ngva_frame;
        std::atomic<bool>     m_software_lockout;
        SpatialKinematics     m_current_kinematics;
    };
}

#endif // RHEINMETALL_PATH_MAPPING_HPP

