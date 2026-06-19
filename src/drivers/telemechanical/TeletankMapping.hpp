#ifndef TELETANK_MAPPING_HPP
#define TELETANK_MAPPING_HPP

#include <cstdint>
#include <atomic>

namespace TeletankCore {

    // Universal Telemechanical Command Bitmask (1930s-1950s Discrete Control Frequencies)
    // Map directly to legacy hardware coils via the UNIVAC parallel register
    struct TeletankCommandBits {
        static constexpr uint32_t PROPULSION_MASK = 0x00000003; // Bits 0-1: Speed steps
        static constexpr uint32_t DIRECTION_MASK  = 0x00000004; // Bit 2: FWD (1) / REV (0)
        static constexpr uint32_t VALVE_LEFT_MASK  = 0x00000008; // Bit 3: Left ballast solenoid
        static constexpr uint32_t VALVE_RIGHT_MASK = 0x00000010; // Bit 4: Right ballast solenoid
        static constexpr uint32_t AUX_PUMP_MASK    = 0x00000020; // Bit 5: Main fluid transfer pump
        static constexpr uint32_t WATCHDOG_BIT     = 0x00000040; // Bit 6: Heartbeat validation bit
        static constexpr uint32_t SAFETY_TRIP_MASK = 0x80000000; // Bit 31: Hard-wired panic loop
    };

    // Raw Telemetry Array processed via Chrysler Multi-Pin Connectors
    struct AerospaceGuidanceTelemetry {
        std::atomic<int32_t> raw_synchro_pitch_volts; // Pitch angle scaled to millivolts
        std::atomic<int32_t> raw_synchro_roll_volts;  // Roll angle scaled to millivolts
        std::atomic<int32_t> lateral_g_accelerometer; // Lateral force output
    };

    /**
     * @class TeletankBridgeProcessor
     * @brief Serializes abstract telemechanical states into legacy raw hardware registers.
     */
    class TeletankBridgeProcessor {
    public:
        TeletankBridgeProcessor() : m_hardware_bus_register(0) {}
        ~TeletankBridgeProcessor() = default;

        // Packs discrete command variables into a single 32-bit legacy parallel payload
        uint32_t serialize_command_packet(uint8_t engine_step, bool forward, bool pump_left, bool pump_right, bool watchdog_state) {
            uint32_t packed_bits = 0;

            packed_bits |= (engine_step & TeletankCommandBits::PROPULSION_MASK);
            if (forward)    packed_bits |= TeletankCommandBits::DIRECTION_MASK;
            if (pump_left)  packed_bits |= TeletankCommandBits::VALVE_LEFT_MASK;
            if (pump_right) packed_bits |= TeletankCommandBits::VALVE_RIGHT_MASK;
            if (pump_left || pump_right) packed_bits |= TeletankCommandBits::AUX_PUMP_MASK;
            if (watchdog_state) packed_bits |= TeletankCommandBits::WATCHDOG_BIT;

            m_hardware_bus_register.store(packed_bits);
            return packed_bits;
        }

        // Returns current 1957 Model 17 phone-jack bus register value
        uint32_t get_active_bus_state() const { return m_hardware_bus_register.load(); }

    private:
        std::atomic<uint32_t> m_hardware_bus_register; // Maps directly to UNIVAC register 17
    };
}

#endif // TELETANK_MAPPING_HPP
