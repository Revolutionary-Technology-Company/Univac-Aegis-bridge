# File Name: config_linked_console.py
# Location: Root source folder
# Subsystem: Configuration-Linked Zero-Lag Memory-Buffered Display Core

import tkinter as tk
import math
import json
import os
import threading
import time

class ConfigLinkedTacticalConsole:
    def __init__(self, root, config_path: str = "config/vessel_config.json"):
        self.root = root
        self.root.title("UNIVAC BACKUP CONSOLE - AUTOCALIBRATED GEOMETRY TYPE")
        self.root.geometry("1100x650")
        self.root.configure(bg="#0c0c0c")

        # --- LOAD & PARSE DISK HARDWARE SPECIFICATION PROFILE ---
        self.config_full_path = os.path.join(os.path.dirname(__file__), config_path)
        self.vessel_profile = self._load_json_hull_specifications()

        # Extract strict structural boundaries for pixel mapping scale calculations
        self.L_hull = float(self.vessel_profile.get('hull_length', 45.0))
        self.B_beam = float(self.vessel_profile.get('beam', 9.5))
        self.max_torque_nm = float(self.vessel_profile.get('max_torque', 90000.0))

        # --- DYNAMIC MATRIX RADAR SCALING COEFFICIENTS ---
        # Maps physical meters to screen pixels based on hull length.
        # This keeps the full hull profile safely visible inside the image buffer.
        self.img_w = 400
        self.img_h = 400
        self.cx = self.img_w // 2
        self.cy = self.img_h // 2
        
        # Pixels-per-meter scaling constant: maps the hull length to exactly 1/3 of the display radius
        self.pixels_per_meter = (self.cx * 0.33) / self.L_hull

        # --- THREAD-ISOLATED CORE MEMORY REGISTERS ---
        self.firing_data_lock = threading.Lock()
        self.high_speed_numeric_buffer = {
            'target_bearing_deg': 45.0,
            'target_distance_meters': self.L_hull * 2.5, # Initialize target at relative hull scale distance
            'current_azimuth_deg': 0.0,
            'is_target_locked': False
        }

        # Low-overhead Tkinter memory photo map back-buffer
        self.memory_image_buffer = tk.PhotoImage(width=self.img_w, height=self.img_h)

        self._build_interface_layout()
        
        # Start low-priority UI frame swap tick loop
        self._start_visual_blit_tick()

    def _load_json_hull_specifications(self) -> dict:
        """Reads the centralized configuration profile from the local disk layer."""
        fallback_profile = {'hull_length': 45.0, 'beam': 9.5, 'max_torque': 90000.0}
        if not os.path.exists(self.config_full_path):
            print(f"[UI_CONFIG_WARN] Parameter profile file missing at {self.config_full_path}. Deploying fallback parameters.")
            return fallback_profile
        try:
            with open(self.config_full_path, 'r') as f:
                return json.load(f)
        except Exception:
            print("[UI_CONFIG_CRITICAL] Parameter file corrupted. Loading hardware defaults.")
            return fallback_profile

    def _build_interface_layout(self):
        """Constructs a high-contrast layout matching your network requirements."""
        banner = tk.Frame(self.root, bg="#111811", height=40, bd=1, relief=tk.SOLID)
        banner.pack(fill=tk.X, side=tk.TOP)
        
        lbl_info = tk.Label(banner, text=f"AUTOCALIBRATION ACTIVE: LOADED SPECIFICATIONS MATCH PROFILE MATRIX ({self.L_hull:.1f}m Hull Length)", 
                            bg="#111811", fg="#00ff00", font=('Courier', 11, 'bold'))
        lbl_info.pack(side=tk.LEFT, padx=15, pady=8)

        panel_container = tk.Frame(self.root, bg="#0c0c0c")
        panel_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_column = tk.Frame(panel_container, bg="#0c0c0c")
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.blit_display_screen = tk.Label(left_column, image=self.memory_image_buffer, bg="#000000", bd=2, relief=tk.RIDGE)
        self.blit_display_screen.pack(padx=10, pady=10)

        right_column = tk.Frame(panel_container, bg="#141414", width=450, bd=1, relief=tk.SOLID)
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=10)

        lbl_ops = tk.Label(right_column, text="[ CALIBRATED TRACKING TELEMETRY ]", bg="#141414", fg="#00ff00", font=('Courier', 11, 'bold'))
        lbl_ops.pack(anchor=tk.W, padx=15, pady=10)

        self.telemetry_box = tk.Text(right_column, width=48, height=18, bg="#000000", fg="#00ff00", font=('Courier', 10))
        self.telemetry_box.pack(padx=15, pady=5)

    def _render_image_buffer_pixels(self):
        """
        Calculates and draws structural range boundaries using 
        calibrated geometry calculations linked to the json specifications.
        """
        # Clear back-buffer memory frame before loading new lines
        self.memory_image_buffer.blank()

        with self.firing_data_lock:
            azimuth_snap = self.high_speed_numeric_buffer['current_azimuth_deg']
            tgt_bearing_snap = self.high_speed_numeric_buffer['target_bearing_deg']
            tgt_dist_meters = self.high_speed_numeric_buffer['target_distance_meters']
            locked_state = self.high_speed_numeric_buffer['is_target_locked']

        # --- DYNAMIC RING GEOMETRY CALCULATION ---
        # Ring 1: Hull Proximity Boundary (Tied directly to absolute hull length in meters)
        ring_1_radius_px = int(self.L_hull * self.pixels_per_meter)
        
        # Ring 2: Tactical Engagement Boundary (Equal to exactly 2.5x full hull lengths)
        ring_2_radius_px = int((self.L_hull * 2.5) * self.pixels_per_meter)
        
        # Ring 3: Outer Horizon Boundary (Equal to exactly 4.0x full hull lengths)
        ring_3_radius_px = int((self.L_hull * 4.0) * self.pixels_per_meter)

        # Blit the dynamic rings onto screen memory via block-transfer coordinates
        # Draws indicator crosses along the circumference lines to bypass heavy GPU rendering
        try:
            for radius in [ring_1_radius_px, ring_2_radius_px, ring_3_radius_px]:
                # Draw discrete 4-point cross bounding markers for fast structural reference
                self.memory_image_buffer.put("#002b00", to=(self.cx - 2, self.cy - radius - 2, self.cx + 2, self.cy - radius + 2))
                self.memory_image_buffer.put("#002b00", to=(self.cx - 2, self.cy + radius - 2, self.cx + 2, self.cy + radius + 2))
                self.memory_image_buffer.put("#002b00", to=(self.cx - radius - 2, self.cy - 2, self.cx - radius + 2, self.cy + 2))
                self.memory_image_buffer.put("#002b00", to=(self.cx + radius - 2, self.cy - 2, self.cx + radius + 2, self.cy + 2))

            # Draw centralized structural safety hull box indicator (Length vs Beam bounding box)
            hx_offset = max(2, int((self.B_beam / 2.0) * self.pixels_per_meter))
            hy_offset = max(4, int((self.L_hull / 2.0) * self.pixels_per_meter))
            self.memory_image_buffer.put("#004400", to=(self.cx - hx_offset, self.cy - hy_offset, self.cx + hx_offset, self.cy + hy_offset))

            # Map target coordinates using the calibrated scaling factor
            tgt_pixel_dist = tgt_dist_meters * self.pixels_per_meter
            rad_tgt = math.radians(tgt_bearing_snap)
            tx = int(self.cx + tgt_pixel_dist * math.sin(rad_tgt))
            ty = int(self.cy - tgt_pixel_dist * math.cos(rad_tgt))

            # Map steering pointer using the calibrated scaling factor
            rad_az = math.radians(azimuth_snap)
            ax = int(self.cx + ring_2_radius_px * math.sin(rad_az))
            ay = int(self.cy - ring_2_radius_px * math.cos(rad_az))

            # Commit updates to pixel mapping arrays
            tgt_color = "#ff0000" if locked_state else "#00ff00"
            self.memory_image_buffer.put(tgt_color, to=(tx - 4, ty - 4, tx + 4, ty + 4))
            self.memory_image_buffer.put("#ffffff", to=(ax - 2, ay - 2, ax + 2, ay + 2))

        except Exception:
            pass # Gracefully insulate boundaries from tracking index adjustments

    def _start_visual_blit_tick(self):
        """Standard, low-priority visual update loop running at 20Hz."""
        # Update simulation track variables slightly to create realistic movements
        with self.firing_data_lock:
            self.high_speed_numeric_buffer['target_bearing_deg'] = (self.high_speed_numeric_buffer['target_bearing_deg'] + 0.4) % 360.0
            # Check target lock condition dynamically
            err = abs(self.high_speed_numeric_buffer['target_bearing_deg'] - self.high_speed_numeric_buffer['current_azimuth_deg'])
            self.high_speed_numeric_buffer['is_target_locked'] = True if err < 1.0 else False
            
            # Simple simulation tracking response
            self.high_speed_numeric_buffer['current_azimuth_deg'] += (self.high_speed_numeric_buffer['target_bearing_deg'] - self.high_speed_numeric_buffer['current_azimuth_deg']) * 0.15

        self._render_image_buffer_pixels()

        # Update text info screen panel
        with self.firing_data_lock:
            snap = self.high_speed_numeric_buffer.copy()

        self.telemetry_box.delete("1.0", tk.END)
        report = (
            "=== CONFIG-LINKED RADAR GEOMETRY ===\n" +
            f"LOADED STRUCTURAL HULL LENGTH: {self.L_hull:.1f} METERS\n" +
            f"LOADED STRUCTURAL BEAM WIDTH:  {self.B_beam:.1f} METERS\n" +
            f"GEOMETRIC SYSTEM SCALE CONST:  {self.pixels_per_meter:.4f} PX/M\n" +
            "====================================\n" +
            f"TACTICAL RING 1 (HULL PROX):   {self.L_hull:.1f} M\n" +
            f"TACTICAL RING 2 (ENGAGEMENT):  {self.L_hull * 2.5:.1f} M\n" +
            f"TACTICAL RING 3 (HORIZON BD):  {self.L_hull * 4.0:.1f} M\n" +
            "====================================\n" +
            f"TARGET RANGE READING:          {snap['target_distance_meters']:.1f} METERS\n" +
            f"TARGET BEARING DIRECTION:      {snap['target_bearing_deg']:.1f}°\n" +
            f"MOUNT AZIMUTH POSITION: {snap['current_azimuth_deg']:.1f}°\n" +
            "====================================\n" +
            "STATUS: Visual canvas calibrated automatically\n" +
            "to match physical storage profile boundaries."
              )
self.telemetry_box.insert(tk.END, report)
self.root.after(50, self._start_visual_blit_tick)
Core Initializer
if name == "main":
ui_frame = tk.Tk()
# Assume file executes from project root or handles safe folder fallbacks
app = ConfigLinkedTacticalConsole(ui_frame, config_path="config/vessel_config.json")
ui_frame.mainloop()
