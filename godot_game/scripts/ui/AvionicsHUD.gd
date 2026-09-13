class_name AvionicsHUD
extends CanvasLayer

## Drosophila Avionics Cockpit HUD & 3D Holographic Connectome Interface
## High-fidelity biological glassmorphism UI displaying real-time Central Complex CANN telemetry:
##   - 360-deg vector compass rose & cardinal heading
##   - CANN bump coherence stability meter
##   - P-EN differential shifter torque deflection gauge (2.09x ratio)
##   - Antennal lobe odor concentration & relative bearing radar (Psi)
##   - Metabolic energy & food foraging score
##   - Holographic 3D connectome viewport with interactive orbit controls & Split Telemetry view
##   - Compound eye hexagonal chromatic FPV post-processing filter

@export var fly_agent: FlyAgent:
	set(val):
		fly_agent = val
		if is_inside_tree() and fly_agent:
			if not fly_agent.telemetry_updated.is_connected(_on_telemetry_updated):
				fly_agent.telemetry_updated.connect(_on_telemetry_updated)
			if not fly_agent.mode_changed.is_connected(_on_flight_mode_changed):
				fly_agent.mode_changed.connect(_on_flight_mode_changed)

@export var camera_controller: FlightCameraController:
	set(val):
		camera_controller = val
		if is_inside_tree() and camera_controller:
			if not camera_controller.camera_mode_changed.is_connected(_on_camera_mode_changed):
				camera_controller.camera_mode_changed.connect(_on_camera_mode_changed)
			if not camera_controller.fpv_intensity_changed.is_connected(set_fpv_intensity):
				camera_controller.fpv_intensity_changed.connect(set_fpv_intensity)

# Sub-components
@onready var fpv_color_rect: ColorRect = $FPVOverlay
@onready var telemetry_panel: PanelContainer = $RootControl/TelemetryPanel
@onready var compass_widget: CompassWidget = $RootControl/TelemetryPanel/VBox/CompassMargin/CompassWidget
@onready var hologram_panel: PanelContainer = $RootControl/HologramPanel
@onready var hologram_viewport: SubViewport = $RootControl/HologramPanel/VBox/HoloContainer/HologramSubViewport
@onready var brain_hologram: BrainHologram = $RootControl/HologramPanel/VBox/HoloContainer/HologramSubViewport/BrainHologram
@onready var help_panel: PanelContainer = $RootControl/HelpPanel

# UI Labels & Gauges
@onready var label_heading: Label = $RootControl/TelemetryPanel/VBox/HeaderBox/LabelHeading
@onready var label_mode: Label = $RootControl/TelemetryPanel/VBox/HeaderBox/LabelMode
@onready var bar_coherence: ProgressBar = $RootControl/TelemetryPanel/VBox/GaugesBox/CoherenceBar
@onready var label_coherence: Label = $RootControl/TelemetryPanel/VBox/GaugesBox/CoherenceBar/LabelCoherence
@onready var bar_shifter_l: ProgressBar = $RootControl/TelemetryPanel/VBox/GaugesBox/ShifterBox/ShifterBarL
@onready var bar_shifter_r: ProgressBar = $RootControl/TelemetryPanel/VBox/GaugesBox/ShifterBox/ShifterBarR
@onready var label_shifter: Label = $RootControl/TelemetryPanel/VBox/GaugesBox/LabelShifter
@onready var bar_odor: ProgressBar = $RootControl/TelemetryPanel/VBox/GaugesBox/OdorBar
@onready var label_odor: Label = $RootControl/TelemetryPanel/VBox/GaugesBox/OdorBar/LabelOdor
@onready var bar_energy: ProgressBar = $RootControl/TelemetryPanel/VBox/GaugesBox/EnergyBar
@onready var label_energy: Label = $RootControl/TelemetryPanel/VBox/GaugesBox/EnergyBar/LabelEnergy
@onready var label_flight_telemetry: Label = $RootControl/TelemetryPanel/VBox/FooterBox/LabelFlightStats
@onready var label_cam_mode: Label = $RootControl/TelemetryPanel/VBox/FooterBox/LabelCamMode
@onready var label_holo_stats: Label = $RootControl/HologramPanel/VBox/TitleBar/LabelHoloStats

var _is_split_view: bool = false
var _fpv_mat: ShaderMaterial
var _fps_update_timer: float = 0.0

func _ready() -> void:
	if not brain_hologram:
		brain_hologram = get_node_or_null("RootControl/HologramPanel/VBox/HoloContainer/HologramSubViewport/BrainHologram")
	if not fpv_color_rect:
		fpv_color_rect = get_node_or_null("FPVOverlay")
	if fpv_color_rect:
		_fpv_mat = fpv_color_rect.material as ShaderMaterial

	if camera_controller:
		if not camera_controller.camera_mode_changed.is_connected(_on_camera_mode_changed):
			camera_controller.camera_mode_changed.connect(_on_camera_mode_changed)
		if not camera_controller.fpv_intensity_changed.is_connected(set_fpv_intensity):
			camera_controller.fpv_intensity_changed.connect(set_fpv_intensity)

	if fly_agent:
		if not fly_agent.telemetry_updated.is_connected(_on_telemetry_updated):
			fly_agent.telemetry_updated.connect(_on_telemetry_updated)
		if not fly_agent.mode_changed.is_connected(_on_flight_mode_changed):
			fly_agent.mode_changed.connect(_on_flight_mode_changed)

	if help_panel:
		help_panel.visible = false

	_setup_glassmorphism_styles()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_H or event.keycode == KEY_F1:
			if help_panel:
				help_panel.visible = not help_panel.visible

func _setup_glassmorphism_styles() -> void:
	# Build sci-fi dark glass panel styling with glowing borders
	var glass_style := StyleBoxFlat.new()
	glass_style.bg_color = Color(0.025, 0.055, 0.09, 0.82)
	glass_style.border_color = Color(0.18, 0.72, 0.95, 0.55)
	glass_style.border_width_left = 2
	glass_style.border_width_top = 2
	glass_style.border_width_right = 2
	glass_style.border_width_bottom = 2
	glass_style.corner_radius_top_left = 8
	glass_style.corner_radius_top_right = 8
	glass_style.corner_radius_bottom_left = 8
	glass_style.corner_radius_bottom_right = 8
	glass_style.shadow_color = Color(0.05, 0.45, 0.85, 0.25)
	glass_style.shadow_size = 12

	if telemetry_panel:
		telemetry_panel.add_theme_stylebox_override("panel", glass_style)
	if hologram_panel:
		hologram_panel.add_theme_stylebox_override("panel", glass_style)
	if help_panel:
		help_panel.add_theme_stylebox_override("panel", glass_style)

func _process(delta: float) -> void:
	if not is_instance_valid(fly_agent):
		return

	# Stream live neural activations into 3D Hologram
	if brain_hologram and fly_agent.cann:
		var speed_frac: float = fly_agent.velocity.length() / max(0.1, fly_agent.max_airspeed)
		var sun_bearing: float = DualRingAttractor.ang_dist(fly_agent.sun_azimuth, fly_agent.rotation.y)
		brain_hologram.update_activations(
			fly_agent.cann,
			speed_frac,
			fly_agent.odor_bearing,
			fly_agent.odor_strength,
			sun_bearing,
			fly_agent.sun_active,
			delta
		)

	# Update live gauges
	_update_gauges(delta)

func _update_gauges(_delta: float) -> void:
	if not fly_agent:
		return

	# 1. Heading & Cardinal
	var h_deg: float = rad_to_deg(fly_agent.rotation.y)
	var norm_deg: float = fposmod(h_deg, 360.0)
	var cardinal: String = _get_cardinal_name(norm_deg)
	if label_heading:
		label_heading.text = "HDG: %03d° %s" % [int(norm_deg), cardinal]

	# 2. Compass Widget
	if compass_widget:
		compass_widget.update_telemetry(
			norm_deg,
			fly_agent.odor_bearing,
			fly_agent.odor_strength,
			fly_agent.sun_azimuth,
			fly_agent.sun_active
		)

	# 3. CANN Bump Coherence
	if bar_coherence and label_coherence:
		var coh_pct: float = fly_agent.bump_coherence * 100.0
		bar_coherence.value = coh_pct
		label_coherence.text = "COHERENCE: %4.1f%%" % coh_pct

	# 4. P-EN Shifter Torque Deflection
	if fly_agent.cann and bar_shifter_l and bar_shifter_r and label_shifter:
		var shifter_acts: Vector2 = fly_agent.cann.get_shifter_activities()
		var s_l: float = shifter_acts.x
		var s_r: float = shifter_acts.y
		bar_shifter_l.value = clamp(s_l * 20.0, 0.0, 100.0)
		bar_shifter_r.value = clamp(s_r * 20.0, 0.0, 100.0)
		var diff: float = s_r - s_l
		var diff_str: String = "BALANCED"
		if diff > 0.15:
			diff_str = "RIGHT (+%2.1f)" % (diff * 2.09)
		elif diff < -0.15:
			diff_str = "LEFT (+%2.1f)" % (-diff * 2.09)
		label_shifter.text = "P-EN SHIFTER TORQUE: %s" % diff_str

	# 5. Odor Concentration
	if bar_odor and label_odor:
		var odor_pct: float = fly_agent.odor_strength * 100.0
		bar_odor.value = odor_pct
		var psi_deg: int = int(rad_to_deg(fly_agent.odor_bearing))
		label_odor.text = "ODOR PLUME: %3.0f%%  (Ψ: %d°)" % [odor_pct, psi_deg]

	# 6. Flight Stats
	if label_flight_telemetry:
		var speed: float = fly_agent.velocity.length()
		var alt: float = fly_agent.global_position.y
		label_flight_telemetry.text = "AIRSPEED: %2.1f u/s | ALT: %2.2f m | THR: %2.0f%%" % [
			speed, alt, fly_agent.throttle * 100.0
		]

	# 7. Hologram Header Readout
	_fps_update_timer += _delta
	if _fps_update_timer > 0.2 and label_holo_stats and fly_agent.cann:
		_fps_update_timer = 0.0
		var fps: int = int(Engine.get_frames_per_second())
		label_holo_stats.text = "CONNECTOME 3D | %d FPS | 1,920 NODES" % fps

func _get_cardinal_name(deg: float) -> String:
	var dirs := ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
	var idx: int = int(round(deg / 45.0)) % 8
	return dirs[idx]

func _on_telemetry_updated(_deg: float, _coh: float, _odor: float, mode_str: String) -> void:
	if label_mode:
		label_mode.text = "[ %s ]" % mode_str
		if mode_str.begins_with("AUTO"):
			label_mode.modulate = Color(0.18, 0.98, 0.55) # Emerald
		else:
			label_mode.modulate = Color(0.20, 0.85, 1.00) # Cyan

func _on_flight_mode_changed(_mode: FlyAgent.FlightMode) -> void:
	pass

func _on_camera_mode_changed(new_mode: FlightCameraController.CameraMode) -> void:
	if label_cam_mode:
		match new_mode:
			FlightCameraController.CameraMode.CHASE:
				label_cam_mode.text = "CAM: [1: CHASE]"
				_set_split_view_layout(false)
			FlightCameraController.CameraMode.FPV:
				label_cam_mode.text = "CAM: [2: FPV]"
				_set_split_view_layout(false)
			FlightCameraController.CameraMode.ORBIT:
				label_cam_mode.text = "CAM: [3: MACRO ORBIT]"
				_set_split_view_layout(false)
			FlightCameraController.CameraMode.SPLIT:
				label_cam_mode.text = "CAM: [4: SPLIT TELEMETRY]"
				_set_split_view_layout(true)

func _set_split_view_layout(split_active: bool) -> void:
	_is_split_view = split_active
	if not hologram_panel:
		return

	if _is_split_view:
		# Expand Hologram Panel to fill entire right 50% of the screen
		hologram_panel.anchor_left = 0.50
		hologram_panel.anchor_top = 0.02
		hologram_panel.anchor_right = 0.98
		hologram_panel.anchor_bottom = 0.98
		hologram_panel.offset_left = 0
		hologram_panel.offset_top = 0
		hologram_panel.offset_right = 0
		hologram_panel.offset_bottom = 0
	else:
		# Return to Top-Right Picture-in-Picture window
		hologram_panel.anchor_left = 1.0
		hologram_panel.anchor_top = 0.0
		hologram_panel.anchor_right = 1.0
		hologram_panel.anchor_bottom = 0.0
		hologram_panel.offset_left = -440
		hologram_panel.offset_top = 20
		hologram_panel.offset_right = -20
		hologram_panel.offset_bottom = 430

func set_fpv_intensity(intensity: float) -> void:
	if _fpv_mat:
		_fpv_mat.set_shader_parameter("intensity", intensity)

func set_metabolic_energy(energy: float, score: int) -> void:
	if bar_energy and label_energy:
		bar_energy.value = energy
		label_energy.text = "NRG: %3.0f%%  |  FOOD: %d" % [energy, score]
		if energy > 50.0:
			bar_energy.modulate = Color(0.2, 0.95, 0.5)
		elif energy > 25.0:
			bar_energy.modulate = Color(1.0, 0.85, 0.2)
		else:
			bar_energy.modulate = Color(1.0, 0.25, 0.25)

## Forward SubViewport mouse input to Brain Hologram 3D camera
func _on_holo_container_gui_input(event: InputEvent) -> void:
	if brain_hologram:
		brain_hologram.handle_gui_input(event)

func _on_btn_expand_pressed() -> void:
	if camera_controller:
		if camera_controller.current_mode == FlightCameraController.CameraMode.SPLIT:
			camera_controller.set_camera_mode(FlightCameraController.CameraMode.CHASE)
		else:
			camera_controller.set_camera_mode(FlightCameraController.CameraMode.SPLIT)

func _on_btn_reset_cam_pressed() -> void:
	if brain_hologram:
		brain_hologram.reset_camera_view()

func _on_btn_help_pressed() -> void:
	if help_panel:
		help_panel.visible = not help_panel.visible
