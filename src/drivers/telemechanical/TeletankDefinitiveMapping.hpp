#ifndef TELETANK_DEFINITIVE_MAPPING_HPP
#define TELETANK_DEFINITIVE_MAPPING_HPP

#include <cstdint>
#include <atomic>

namespace TeletankCore {

    /**
     * @brief The Complete 24-Command "TOZ-IV" Radio Protocol (1930s-1940s)
     * Maps the original Soviet dual-frequency radio pulses to 32-bit parallel flags.
     * 
     * Historical Note: The TT-26 used two frequencies (HF/UHF) to prevent jamming.
     * This mapping merges both frequency bands into a unified digital register.
     */
    struct TeletankCommandBits {
        // --- LOCOMOTION GROUP (Frequency A) ---
        static constexpr uint32_t GEAR_1_CRAWL       = 0x00000001; // 1st Gear (Docking / Precision)
        static constexpr uint32_t GEAR_2_CRUISE      = 0x00000002; // 2nd Gear (Combat Advance)
        static constexpr uint32_t GEAR_3_FAST        = 0x00000004; // 3rd Gear (Transit)
        static constexpr uint32_t GEAR_4_MAX         = 0x00000008; // 4th Gear (Retreat / Evasion)
        static constexpr uint32_t REVERSE_ENGAGE     = 0x00000010; // Reverse Idler Solenoid
        static constexpr uint32_t LEFT_CLUTCH_BRAKE  = 0x00000020; // Hard Left Turn (Skid Steer)
        static constexpr uint32_t RIGHT_CLUTCH_BRAKE = 0x00000040; // Hard Right Turn (Skid Steer)
        static constexpr uint32_t ENGINE_IGNITION    = 0x00000080; // Compressed Air Starter
        static constexpr uint32_t STOP_HOLD          = 0x00000100; // Emergency Mechanical Brake

        // --- TURRET & ARMAMENT GROUP (Frequency B - Standard) ---
        static constexpr uint32_t TURRET_ROTATE_CW   = 0x00000200; // Electric Turret Traverse Right
        static constexpr uint32_t TURRET_ROTATE_CCW  = 0x00000400; // Electric Turret Traverse Left
        static constexpr uint32_t MG_FIRE_SOLENOID   = 0x00000800; // DT-29 Machine Gun Trigger (Fixed or Coax)
        static constexpr uint32_t MAIN_GUN_FIRE      = 0x00001000; // 45mm Cannon Solenoid (If equipped)

        // --- SPECIALIZED "TITAN" MODULES (Frequency B - Auxiliaries) ---
        // TT-26 variants often swapped the main gun for these payloads.
        
        // 1. FLAMETHROWER (KS-24 / KS-25 System)
        static constexpr uint32_t FLAME_IGNITER      = 0x00002000; // Spark plug ignition for nozzle
        static constexpr uint32_t FLAME_PRESSURE     = 0x00004000; // CO2 pressure valve open
        static constexpr uint32_t FLAME_DISCHARGE    = 0x00008000; // Release 200L fuel mixture
        
        // 2. CHEMICAL WARFARE (OV Launchers / Balloons)
        static constexpr uint32_t CHEM_SPRAY_REAR    = 0x00010000; // Rear decontamination/poison dispenser
        static constexpr uint32_t CHEM_DISPENSE_L    = 0x00020000; // Left side gas canister release
        static constexpr uint32_t CHEM_DISPENSE_R    = 0x00040000; // Right side gas canister release
        
        // 3. OBSCURATION
        static constexpr uint32_t SMOKE_SCREEN_GEN   = 0x00080000; // Exhaust injection or canister drop

        // 4. DEMOLITION (TT-26-Sh "Podryvnik")
        // The "Sapper" tank carried a 200-700kg armored bomb box.
        static constexpr uint32_t DROP_DEMO_BOX      = 0x00100000; // Release hydraulic latches on bomb box
        static constexpr uint32_t ARM_DEMO_FUSE      = 0x00200000; // Pull pin / start mechanical timer (15 min)

        // --- SAFETY & TELEMETRY ---
        static constexpr uint32_t WATCHDOG_HEARTBEAT = 0x40000000; // Must toggle every 100ms (30s historical)
        static constexpr uint32_t SELF_DESTRUCT_ARM  = 0x80000000; // Internal scuttling charge (Anti-Capture)
    };

    /**
     * @brief Raw TOZ-IV Telemetry Return Packet
     * The TT-26 sent very limited analog data back to the TU-26 command tank.
     * We map these original limited channels + modern additions.
     */
    struct TeletankTelemetryState {
        // Original 1930s Analog Returns (via primitive radio feedback)
        std::atomic<bool> engine_running;          // Microphone check / RPM buzz
        std::atomic<bool> flame_pressure_ready;    // Pressure switch contact
        std::atomic<bool> demo_box_attached;       // Limit switch on rear deck

        // Modern / Monorail Retrofit Additions (via Chrysler Computer)
        std::atomic<float> chassis_pitch_deg;      // Synchro-resolver output
        std::atomic<float> chassis_roll_deg;       // Synchro-resolver output
        std::atomic<float> lateral_g_force;        // Accelerometer
        std::atomic<float> tank_fluid_level_l;     // Ballast / Fuel / Chem level
        std::atomic<float> tank_fluid_level_r;     // Ballast / Fuel / Chem level
    };

    /**
     * @class TeletankCommandProcessor
     * @brief Translates high-level requests into strict TOZ-IV bitmasks.
     */
    class TeletankCommandProcessor {
    public:
        TeletankCommandProcessor() : m_register_state(0) {}

        // --- LOCOMOTION HELPERS ---
        void set_gear(uint8_t gear) {
            uint32_t clear_mask = ~(TeletankCommandBits::GEAR_1_CRAWL | TeletankCommandBits::GEAR_2_CRUISE | 
                                    TeletankCommandBits::GEAR_3_FAST | TeletankCommandBits::GEAR_4_MAX);
            uint32_t new_bits = m_register_state.load() & clear_mask;
            
            switch(gear) {
                case 1: new_bits |= TeletankCommandBits::GEAR_1_CRAWL; break;
                case 2: new_bits |= TeletankCommandBits::GEAR_2_CRUISE; break;
                case 3: new_bits |= TeletankCommandBits::GEAR_3_FAST; break;
                case 4: new_bits |= TeletankCommandBits::GEAR_4_MAX; break;
                default: break; // Neutral
            }
            m_register_state.store(new_bits);
        }

        // --- MODULE COMMANDS (Monorail Mapped vs Historical) ---
        
        // For Monorail: Maps to "Tele-Tank" Ballast Pumps
        // For TT-26: Maps to "Chemical Dispenser" Solenoids
        void activate_fluid_transfer(bool left, bool right) {
            uint32_t bits = m_register_state.load();
            if (left)  bits |= TeletankCommandBits::CHEM_DISPENSE_L; // Map Left Pump
            else       bits &= ~TeletankCommandBits::CHEM_DISPENSE_L;
            
            if (right) bits |= TeletankCommandBits::CHEM_DISPENSE_R; // Map Right Pump
            else       bits &= ~TeletankCommandBits::CHEM_DISPENSE_R;
            
            m_register_state.store(bits);
        }

        // For Monorail: Maps to Emergency Air Brake Dump
        // For TT-26: Maps to "Drop Demolition Box" (Box drop = Emergency Stop)
        void trigger_emergency_mechanical_action() {
            uint32_t bits = m_register_state.load();
            bits |= TeletankCommandBits::DROP_DEMO_BOX; // Drops air pressure / drops bomb
            bits |= TeletankCommandBits::STOP_HOLD;
            m_register_state.store(bits);
        }

        uint32_t get_register() const { return m_register_state.load(); }

    private:
        std::atomic<uint32_t> m_register_state;
    };
}

#endif // TELETANK_DEFINITIVE_MAPPING_HPP

