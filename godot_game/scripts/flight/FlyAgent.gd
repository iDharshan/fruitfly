class_name FlyAgent
extends CharacterBody3D

## Drosophila 3D Fly Agent
## Fully driven by biological Central Complex CANN continuous attractor dynamics.
## Features 6-DOF biomechanical flight kinematics, saccadic ballistic body turns,
## haltere gyroscopic stabilization, and 200 Hz wing beat acoustic synthesis.

enum FlightMode { MANUAL, AUTO_PFL3 }

@export var mode: FlightMode = FlightMode.MANUAL
@export var max_airspeed: float = 4.2 # units / sec (~1.4 m/s biological macro scale)
@export var acceleration: float = 9.0
@export var drag_coefficient: float = 2.4
@export var lift_coefficient: float = 2.0
@export var haltere_damping: float = 4.5 # Gyroscopic rate damping

# Biological CANN Circuit
var cann: DualRingAttractor
var decoded_heading: float = 0.0
var bump_coherence: float = 0.85
var bump_amplitude: float = 1.8

# Animation & Visual Nodes
var _fly_model: Node3D
var _left_wing_root: Node3D
var _right_wing_root: Node3D
var _left_haltere_root: Node3D
var _right_haltere_root: Node3D
var _left_wing_mat: ShaderMaterial
var _right_wing_mat: ShaderMaterial

# Audio
var _audio_buzz: WingAudioSynthesizer

# Flight State
var throttle: float = 0.35 # Start with gentle cruise hover
var target_throttle: float = 0.35
var pitch_input: float = 0.0
var roll_input: float = 0.0
var vertical_input: float = 0.0
var steer_omega: float = 0.0 # Angular velocity drive into CANN shifters

# Saccadic Mechanics
var _is_saccading: bool = false
var _saccade_timer: float = 0.0
var _current_yaw_rate: float = 0.0

# 200 Hz Wing Flap State
var _wing_phase: float = 0.0
var _left_wing_amp: float = 0.22
var _right_wing_amp: float = 0.22

# External Sensory Inputs
var odor_bearing: float = 0.0
var odor_strength: float = 0.0
var sun_azimuth: float = 0.0
var sun_active: bool = false

# Camera Mounts
@onready var chase_cam_mount: Marker3D = $ChaseCamMount
@onready var cockpit_cam_mount: Marker3D = $CockpitCamMount

signal mode_changed(new_mode: FlightMode)
signal telemetry_updated(heading_deg: float, coherence: float, odor_conc: float, mode_name: String)

func _ready() -> void:
	# 1. Initialize Biological CANN Continuous Attractor
	cann = DualRingAttractor.new()
	cann.reset(rotation.y)
	
	# 2. Procedural Drosophila Mesh Generation
	_fly_model = FlyMeshGenerator.generate_fly()
	add_child(_fly_model)
	
	_left_wing_root = _fly_model.get_node_or_null("LeftWingRoot")
	_right_wing_root = _fly_model.get_node_or_null("RightWingRoot")
	_left_haltere_root = _fly_model.get_node_or_null("LeftHaltereRoot")
	_right_haltere_root = _fly_model.get_node_or_null("RightHaltereRoot")
	
	if _left_wing_root:
		var left_wing_mesh: MeshInstance3D = _left_wing_root.get_node_or_null("LeftWing")
		if left_wing_mesh:
			_left_wing_mat = left_wing_mesh.material_override as ShaderMaterial
			
	if _right_wing_root:
		var right_wing_mesh: MeshInstance3D = _right_wing_root.get_node_or_null("RightWing")
		if right_wing_mesh:
			_right_wing_mat = right_wing_mesh.material_override as ShaderMaterial
			
	# 3. Procedural Wing Acoustics
	_audio_buzz = WingAudioSynthesizer.new()
	_audio_buzz.name = "WingAudio"
	add_child(_audio_buzz)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_mode"):
		toggle_flight_mode()
	elif event.is_action_pressed("reset_flight"):
		reset_flight_state()

func toggle_flight_mode() -> void:
	if mode == FlightMode.MANUAL:
		mode = FlightMode.AUTO_PFL3
	else:
		mode = FlightMode.MANUAL
	mode_changed.emit(mode)
	print("Flight mode switched to: ", FlightMode.keys()[mode])

func reset_flight_state() -> void:
	velocity = Vector3.ZERO
	throttle = 0.35
	target_throttle = 0.35
	rotation = Vector3.ZERO
	if cann:
		cann.reset(0.0)

func _process(delta: float) -> void:
	# 200 Hz Wingbeat Phase Integration
	var current_freq: float = lerp(190.0, 245.0, throttle)
	_wing_phase = fmod(_wing_phase + delta * current_freq * TAU, TAU)
	
	# Update Shader Wing Vertex Flapping
	if _left_wing_mat:
		_left_wing_mat.set_shader_parameter("wing_phase", _wing_phase)
		_left_wing_mat.set_shader_parameter("flutter_amplitude", _left_wing_amp)
	if _right_wing_mat:
		_right_wing_mat.set_shader_parameter("wing_phase", _wing_phase)
		_right_wing_mat.set_shader_parameter("flutter_amplitude", _right_wing_amp)
		
	# Physical Wing Root Sweeping Motion (Stroke Plane Angle)
	var stroke_swing: float = sin(_wing_phase) * 0.35 * (0.6 + 0.4 * throttle)
	if _left_wing_root:
		_left_wing_root.rotation.z = stroke_swing
		_left_wing_root.rotation.y = -stroke_swing * 0.4
	if _right_wing_root:
		_right_wing_root.rotation.z = -stroke_swing
		_right_wing_root.rotation.y = stroke_swing * 0.4
		
	# Haltere Gyroscopic Antiphase Oscillation
	var haltere_swing: float = -cos(_wing_phase) * 0.45
	if _left_haltere_root:
		_left_haltere_root.rotation.x = haltere_swing
	if _right_haltere_root:
		_right_haltere_root.rotation.x = -haltere_swing
		
	# Modulate Audio Buzz
	if _audio_buzz:
		_audio_buzz.set_flight_throttle(throttle, true)
		
	# Emit Telemetry signal for HUD
	var mode_name: String = "AUTO PFL3" if mode == FlightMode.AUTO_PFL3 else "MANUAL"
	telemetry_updated.emit(rad_to_deg(rotation.y), bump_coherence, odor_strength, mode_name)

func _physics_process(delta: float) -> void:
	# 1. Gather User or AI Navigation Inputs
	_update_flight_inputs(delta)
	
	# 2. Integrate Continuous Attractor Neural Dynamics (CANN)
	if cann:
		cann.step_frame(delta, steer_omega, sun_azimuth, sun_active)
		var h_data: Dictionary = cann.decode_heading()
		decoded_heading = h_data["heading"]
		bump_coherence = h_data["coherence"]
		bump_amplitude = h_data["amplitude"]
		
	# 3. Couple CANN Heading to Physical Fly Body (Connectome Steering)
	_apply_neural_steering(delta)
	
	# 4. Integrate 6-DOF Biomechanical Flight Forces
	_integrate_aerodynamics(delta)
	
	# Move using Godot CharacterBody3D kinematics
	move_and_slide()

func _update_flight_inputs(delta: float) -> void:
	if mode == FlightMode.MANUAL:
		# Player Controls
		# Throttle
		if Input.is_action_pressed("fly_throttle_up"):
			target_throttle = clamp(target_throttle + 0.8 * delta, 0.0, 1.0)
		elif Input.is_action_pressed("fly_brake"):
			target_throttle = clamp(target_throttle - 0.8 * delta, 0.0, 1.0)
			
		# Vertical Lift (Space / Shift)
		vertical_input = 0.0
		if Input.is_action_pressed("fly_climb"):
			vertical_input += 1.0
		if Input.is_action_pressed("fly_dive"):
			vertical_input -= 1.0
			
		# Roll Banking (Q / E)
		roll_input = 0.0
		if Input.is_action_pressed("fly_roll_left"):
			roll_input -= 1.0
		if Input.is_action_pressed("fly_roll_right"):
			roll_input += 1.0
			
		# Yaw Steering -> Drives P-EN Shifters directly!
		steer_omega = 0.0
		if Input.is_action_pressed("fly_yaw_left"):
			steer_omega -= 2.8 # Injects leftward angular velocity into P-EN_L
		if Input.is_action_pressed("fly_yaw_right"):
			steer_omega += 2.8 # Injects rightward angular velocity into P-EN_R
			
	else:
		# Autonomous Biological PFL3 Chemotaxis / Phototaxis Mode
		if cann:
			var pfl3_res: Dictionary = cann.step_pfl3(odor_bearing, odor_strength, delta)
			steer_omega = pfl3_res["omega_auto"]
			
			# Modulate throttle based on odor distance and alignment
			var cos_psi: float = cos(odor_bearing)
			target_throttle = lerp(0.35, 0.95, (0.5 + 0.5 * cos_psi) * (0.3 + 0.7 * odor_strength))
			vertical_input = 0.0

func _apply_neural_steering(delta: float) -> void:
	# Compute angular error between decoded internal compass bump and physical body heading
	var body_heading: float = rotation.y
	var heading_error: float = DualRingAttractor.ang_dist(decoded_heading, body_heading)
	
	# Saccadic Turn Gating (Currea et al. 2026):
	# If error exceeds 30 degrees (0.52 rad), trigger rapid ballistic saccade turn
	if abs(heading_error) > 0.52:
		_is_saccading = true
		_saccade_timer = 0.06 # 60 ms biological saccade burst
		# Asymmetric Wingbeat Amplitude (Outer wing beats harder)
		if heading_error > 0.0:
			_left_wing_amp = 0.32  # Left outer wing increases stroke
			_right_wing_amp = 0.12 # Right inner wing decreases stroke
		else:
			_left_wing_amp = 0.12
			_right_wing_amp = 0.32
	else:
		_is_saccading = false
		_left_wing_amp = lerp(_left_wing_amp, 0.22, delta * 8.0)
		_right_wing_amp = lerp(_right_wing_amp, 0.22, delta * 8.0)
		
	# Proportional Steering Drive with Saccadic Multiplier
	var steer_gain: float = 12.0 if _is_saccading else 5.5
	var target_yaw_rate: float = clamp(heading_error * steer_gain, -18.0, 18.0) # Up to ~1000 deg/s
	
	# Haltere Gyroscopic Coriolis Damping:
	# Dampens high angular velocity to prevent overshoot and stabilize on target heading
	var gyro_damping: float = -_current_yaw_rate * haltere_damping
	_current_yaw_rate = lerp(_current_yaw_rate, target_yaw_rate + gyro_damping * delta, delta * 12.0)
	
	# Apply Yaw Rotation
	rotate_y(_current_yaw_rate * delta)
	
	# Coordinated Aerodynamic Banking Roll into Yaw Turns
	var target_roll: float = -_current_yaw_rate * 0.12
	rotation.z = lerp(rotation.z, target_roll + roll_input * 0.35, delta * 6.0)

func _integrate_aerodynamics(delta: float) -> void:
	# Throttle Damping
	throttle = move_toward(throttle, target_throttle, acceleration * delta * 0.5)
	
	# Directional Vectors
	var forward_dir: Vector3 = -global_transform.basis.z
	var up_dir: Vector3 = global_transform.basis.y
	
	# Aerodynamic Forces
	var thrust_force: Vector3 = forward_dir * (throttle * max_airspeed)
	var lift_force: Vector3 = up_dir * (vertical_input * lift_coefficient + throttle * 0.35)
	var drag_force: Vector3 = -velocity * drag_coefficient * delta
	
	velocity = velocity.lerp(thrust_force + lift_force, delta * 4.0) + drag_force
