#ifndef BRADLEY_EXCHANGE_MAPPER_HPP
#define BRADLEY_EXCHANGE_MAPPER_HPP

#include <cstdint>
#include <atomic>

namespace BradleyExchangeCore {

    /**
     * @brief Advanced Tactical Auxiliary Command Bitmask
     * Maps the UNIVAC typewriter register to the Bradley Exchange hardware modules.
     */
    struct BradleyModuleBits {
        // --- COOLING & COMMUNICATIONS (AC Delco / Swisscode) ---
        static constexpr uint32_t AC_DELCO_HEADLIGHT_PUMP = 0x00000001; // Bit 0: Headlight nose cooling pump
        static constexpr uint32_t SWISSCODE_COACH_AC_ON  = 0x00000002; // Bit 1: Primary cabin climate power
        static constexpr uint32_t EXPRESS_WIND_MODE       = 0x00000004; // Bit 2: Force max fan venting
        static constexpr uint32_t TURBO_FAN_MODULE        = 0x00000008; // Bit 3: Fan-charged air turbo purge
        static constexpr uint32_t GE_FIBER_CHANNEL_UP    = 0x00000010; // Bit 4: Activate high-speed data stream
        static constexpr uint32_t SIP_COMMS_ACTIVE       = 0x00000020; // Bit 5: Keep VoIP telephony channel open

        // --- MECHANICAL DECOUPLING & DEPLOYMENT ---
        static constexpr uint32_t TRACK_ANCHOR_PULLEY    = 0x00000100; // Bit 8: Pull car from track anchor position
        static constexpr uint32_t DISENGAGE_TRACK_COMP   = 0x00000200; // Bit 9: Retract passive horizontal tires
        static constexpr uint32_t SMOOTH_RAIL_EXPRESS    = 0x00000400; // Bit 10: Smooth rail express execution transit
        static constexpr uint32_t TIRE_CHANGING_MODULE   = 0x00000800; // Bit 11: Engage maintenance tire jack lifters
        static constexpr uint32_t CARGO_BELOW_LOCKS      = 0x00001000; // Bit 12: Secure under-car cargo hold locks
    };

    class BradleyExchangeProcessor {
    public:
        BradleyExchangeProcessor() : m_typewriter_io_bus(0) {}
        ~BradleyExchangeProcessor() = default;

        /**
         * @brief Serializes auxiliary payload states into a single 32-bit word for the UNIVAC typewriter.
         */
        uint32_t compile_typewriter_word(bool ac_delco, bool swiss_ac, bool turbo_fan, bool fiber_channel, 
                                          bool pulley_pull, bool disengage_track, bool tire_jack) {
            uint32_t packed_word = 0;

            // Apply Cooling & Comms Flags
            if (ac_delco)       packed_word |= BradleyModuleBits::AC_DELCO_HEADLIGHT_PUMP;
            if (swiss_ac)       packed_word |= BradleyModuleBits::SWISSCODE_COACH_AC_ON;
            if (turbo_fan)      packed_word |= BradleyModuleBits::TURBO_FAN_MODULE;
            if (fiber_channel)  packed_word |= BradleyModuleBits::GE_FIBER_CHANNEL_UP;

            // Apply Mechanical Decoupling Flags
            if (pulley_pull)    packed_word |= BradleyModuleBits::TRACK_ANCHOR_PULLEY;
            if (disengage_track) packed_word |= BradleyModuleBits::DISENGAGE_TRACK_COMP;
            if (tire_jack)      packed_word |= BradleyModuleBits::TIRE_CHANGING_MODULE;

            // Always enforce cargo locking for safety before execution
            packed_word |= BradleyModuleBits::CARGO_BELOW_LOCKS;
            packed_word |= BradleyModuleBits::SIP_COMMS_ACTIVE;

            m_typewriter_io_bus.store(packed_word);
            return packed_word;
        }

        uint32_t get_active_bus_state() const { return m_typewriter_io_bus.load(); }

    private:
        std::atomic<uint32_t> m_typewriter_io_bus; // Direct memory-mapped register address for terminal
    };
}

#endif // BRADLEY_EXCHANGE_MAPPER_HPP

