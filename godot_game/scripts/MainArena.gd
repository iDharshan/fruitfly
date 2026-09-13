class_name MainArena
extends Node3D

## Main Arena Game Director
## Coordinates real-time sensory streams between the macro environment,
## celestial sun beacon, and the biological CANN-driven Drosophila agent,
## and connects avionics HUD and 3D connectome telemetry.

@onready var fly_agent: FlyAgent = $FlyAgent
@onready var tabletop: MacroTabletop = $MacroTabletop
@onready var sun_beacon: SunBeacon = $SunBeacon3D
@onready var flight_camera: FlightCameraController = $FlightCamera
@onready var avionics_hud: AvionicsHUD = $AvionicsHUD

var food_score: int = 0
var metabolic_energy: float = 100.0 # 0% to 100%

func _ready() -> void:
	print("====================================================================")
	print("       🪰 DROSOPHILA 3D: HIGH-FIDELITY NEURO-FLIGHT GAME 🪰")
	print("  Biological CANN Heading Compass & Biomechanical Flight Engine")
	print("  Renderer : Forward+ Clustered Vulkan | Resolution: 1920x1080")
	print("  Controls : WASD (Throttle/Yaw) | Space/Shift (Climb/Dive)")
	print("             Q/E (Roll) | M (Toggle Auto PFL3) | C/TAB (Camera Views)")
	print("             F11 (Fullscreen) | R (Reset Flight) | T (Sun Beacon)")
	print("====================================================================")

	if tabletop and tabletop.food_piece:
		tabletop.food_piece.food_consumed.connect(_on_food_consumed)
	if sun_beacon and fly_agent:
		sun_beacon.target_fly = fly_agent

	# Connect HUD to Fly and Camera
	if avionics_hud:
		avionics_hud.fly_agent = fly_agent
		avionics_hud.camera_controller = flight_camera
		avionics_hud.set_metabolic_energy(metabolic_energy, food_score)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_fullscreen"):
		var is_fs: bool = DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if is_fs else DisplayServer.WINDOW_MODE_FULLSCREEN)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_T:
		if sun_beacon:
			sun_beacon.toggle_active()

func _physics_process(delta: float) -> void:
	if not is_instance_valid(fly_agent):
		return

	# 1. Stream 3D Bilateral Odor Gradient & Ambient Wind to Fly
	if tabletop and tabletop.odor_field:
		var odor_data: Dictionary = tabletop.odor_field.sample_antennae(
			fly_agent.global_position,
			fly_agent.global_transform.basis
		)
		fly_agent.odor_bearing = odor_data["relative_bearing"]
		fly_agent.odor_strength = odor_data["concentration"]
		fly_agent.ambient_wind = odor_data["wind_vector"]

	# 2. Stream Celestial Sun Azimuth to Fly Compound Eyes
	if sun_beacon:
		fly_agent.sun_active = sun_beacon.is_active
		fly_agent.sun_azimuth = sun_beacon.get_sun_azimuth()

	# 3. Metabolic Energy Depletion
	var throttle_drain: float = lerp(0.8, 3.5, fly_agent.throttle)
	metabolic_energy = max(0.0, metabolic_energy - throttle_drain * delta * 0.4)

	# 4. Stream Energy Telemetry to HUD
	if avionics_hud:
		avionics_hud.set_metabolic_energy(metabolic_energy, food_score)

func _on_food_consumed(_food_pos: Vector3) -> void:
	food_score += 1
	metabolic_energy = min(100.0, metabolic_energy + 35.0) # Replenish energy +35%
	if avionics_hud:
		avionics_hud.set_metabolic_energy(metabolic_energy, food_score)
	print("Food item eaten! Score: ", food_score, " | Energy: ", snapped(metabolic_energy, 0.1), "%")
