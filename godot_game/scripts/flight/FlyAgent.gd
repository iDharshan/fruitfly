class_name FlyAgent
extends CharacterBody3D

## Drosophila 3D Fly Agent
## Driven by biological Central Complex CANN continuous attractor dynamics.
## Features 6-DOF independent 3D flight kinematics with direct vertical climb/dive,
## haltere gyroscopic rate damping, 200 Hz wing acoustics, and 3D chemotaxis.

enum FlightMode { MANUAL, AUTO_PFL3 }
enum AutoNavState { SURGE, CAST, MENOTAXIS }

@export var mode: FlightMode = FlightMode.MANUAL
@export var max_airspeed: float = 6.0 # units / sec
@export var climb_speed: float = 5.5  # vertical climb / dive speed
@export var acceleration: float = 12.0
@export var haltere_damping: float = 4.0

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
var _abdomen_mesh: MeshInstance3D

# Audio
var _audio_buzz: WingAudioSynthesizer

# Flight State
var throttle: float = 0.40
var forward_input: float = 0.0
var vertical_input: float = 0.0
var roll_input: float = 0.0
var steer_omega: float = 0.0
var _current_yaw_rate: float = 0.0
var current_yaw_err: float = 0.0

# 200 Hz Wing Flap State
var _wing_phase: float = 0.0
var _left_wing_amp: float = 0.22
var _right_wing_amp: float = 0.22

# External Sensory Inputs
var odor_bearing: float = 0.0     # Horizontal azimuth error to food
var odor_elevation: float = 0.0   # Vertical pitch error to food
var odor_strength: float = 0.0
var sun_azimuth: float = 0.0
var sun_active: bool = false
var ambient_wind: Vector3 = Vector3(0.12, 0.0, -0.08)
var estimated_wind: Vector3 = Vector3.ZERO
var target_food_pos: Vector3 = Vector3(0.0, 6.0, -8.0)
var food_distance: float = 10.0

# 3D Autonomous Navigation State Machine
var nav_state: AutoNavState = AutoNavState.SURGE
var _cast_timer: float = 0.0
var _cast_duration: float = 1.2
var _cast_direction: float = 1.0
var _last_valid_plume_heading: float = 0.0
var _plume_loss_timer: float = 0.0
const ODOR_DETECTION_THRESH: float = 0.015

# Camera Mounts
@onready var chase_cam_mount: Marker3D = $ChaseCamMount
@onready var cockpit_cam_mount: Marker3D = $CockpitCamMount

signal mode_changed(new_mode: FlightMode)
signal telemetry_updated(heading_deg: float, coherence: float, odor_conc: float, mode_name: String)

func _ready() -> void:
	cann = DualRingAttractor.new()
	cann.reset(rotation.y)
	
	_fly_model = FlyMeshGenerator.generate_fly()
	add_child(_fly_model)
	
	_left_wing_root = _fly_model.get_node_or_null("LeftWingRoot")
	_right_wing_root = _fly_model.get_node_or_null("RightWingRoot")
	_left_haltere_root = _fly_model.get_node_or_null("LeftHaltereRoot")
	_right_haltere_root = _fly_model.get_node_or_null("RightHaltereRoot")
	_abdomen_mesh = _fly_model.get_node_or_null("Abdomen") as MeshInstance3D
	
	if _left_wing_root:
		var left_wing_mesh: MeshInstance3D = _left_wing_root.get_node_or_null("LeftWing")
		if left_wing_mesh:
			_left_wing_mat = left_wing_mesh.material_override as ShaderMaterial
			
	if _right_wing_root:
		var right_wing_mesh: MeshInstance3D = _right_wing_root.get_node_or_null("RightWing")
		if right_wing_mesh:
			_right_wing_mat = right_wing_mesh.material_override as ShaderMaterial
			
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
	rotation = Vector3.ZERO
	forward_input = 0.0
	vertical_input = 0.0
	throttle = 0.40
	nav_state = AutoNavState.SURGE
	_cast_timer = 0.0
	_plume_loss_timer = 0.0
	if cann:
		cann.reset(0.0)

func _process(delta: float) -> void:
	var current_freq: float = lerp(190.0, 245.0, throttle)
	_wing_phase = fmod(_wing_phase + delta * current_freq * TAU, TAU)
	
	if _left_wing_mat:
		_left_wing_mat.set_shader_parameter("wing_phase", _wing_phase)
		_left_wing_mat.set_shader_parameter("flutter_amplitude", _left_wing_amp)
	if _right_wing_mat:
		_right_wing_mat.set_shader_parameter("wing_phase", _wing_phase)
		_right_wing_mat.set_shader_parameter("flutter_amplitude", _right_wing_amp)
		
	var stroke_swing: float = sin(_wing_phase) * 0.35 * (0.6 + 0.4 * throttle)
	if _left_wing_root:
		_left_wing_root.rotation.z = stroke_swing
		_left_wing_root.rotation.y = -stroke_swing * 0.4
	if _right_wing_root:
		_right_wing_root.rotation.z = -stroke_swing
		_right_wing_root.rotation.y = stroke_swing * 0.4
		
	var haltere_swing: float = -cos(_wing_phase) * 0.45
	if _left_haltere_root:
		_left_haltere_root.rotation.x = haltere_swing
	if _right_haltere_root:
		_right_haltere_root.rotation.x = -haltere_swing
		
	# Biological abdominal respiratory pumping
	if _abdomen_mesh:
		var pump: float = sin(_wing_phase * 0.08) * 0.025
		_abdomen_mesh.scale = Vector3(1.0 + pump * 0.4, 1.0 + pump * 0.4, 1.0 - pump)
		
	if _audio_buzz:
		_audio_buzz.set_flight_throttle(throttle, true)
		
	var mode_name: String = "MANUAL [FREE 3D]"
	if mode == FlightMode.AUTO_PFL3:
		match nav_state:
			AutoNavState.SURGE: mode_name = "AUTO [3D SURGE]"
			AutoNavState.CAST: mode_name = "AUTO [3D CAST]"
			AutoNavState.MENOTAXIS: mode_name = "AUTO [3D NAV]"
	telemetry_updated.emit(rad_to_deg(rotation.y), bump_coherence, odor_strength, mode_name)

func _physics_process(delta: float) -> void:
	_update_flight_inputs(delta)
	
	if cann:
		cann.step_frame(delta, steer_omega, sun_azimuth, false)
		var h_data: Dictionary = cann.decode_heading()
		decoded_heading = h_data["heading"]
		bump_coherence = h_data["coherence"]
		bump_amplitude = h_data["amplitude"]
		
	_apply_neural_steering(delta)
	_integrate_3d_flight(delta)
	move_and_slide()

func _update_flight_inputs(delta: float) -> void:
	if mode == FlightMode.MANUAL:
		# --- VERTICAL CLIMB / DIVE (Fly UP / DOWN) ---
		vertical_input = 0.0
		if Input.is_action_pressed("fly_climb") or Input.is_key_pressed(KEY_SPACE) or Input.is_key_pressed(KEY_UP):
			vertical_input += 1.0
		if Input.is_action_pressed("fly_dive") or Input.is_key_pressed(KEY_SHIFT) or Input.is_key_pressed(KEY_CTRL) or Input.is_key_pressed(KEY_DOWN):
			vertical_input -= 1.0
			
		# --- FORWARD / BACKWARD ---
		forward_input = 0.0
		if Input.is_action_pressed("fly_throttle_up") or Input.is_key_pressed(KEY_W):
			forward_input += 1.0
		if Input.is_action_pressed("fly_brake") or Input.is_key_pressed(KEY_S):
			forward_input -= 0.6
			
		# --- YAW TURN (Left / Right) ---
		var input_steer: float = 0.0
		if Input.is_action_pressed("fly_yaw_left") or Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
			input_steer -= 3.5
		if Input.is_action_pressed("fly_yaw_right") or Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
			input_steer += 3.5
		steer_omega = input_steer
		
		# --- BANKING ROLL (Q / E) ---
		roll_input = 0.0
		if Input.is_action_pressed("fly_roll_left") or Input.is_key_pressed(KEY_Q):
			roll_input -= 1.0
		if Input.is_action_pressed("fly_roll_right") or Input.is_key_pressed(KEY_E):
			roll_input += 1.0
			
	else:
		_execute_autonomous_anemotaxis(delta)

func apply_flight_input(yaw_rate: float, thr: float, pitch: float = 0.0) -> void:
	steer_omega = yaw_rate
	throttle = clamp(thr, 0.0, 1.0)
	vertical_input = pitch

func _execute_autonomous_anemotaxis(delta: float) -> void:
	# Calculate 3D target vector in world space
	var delta_pos: Vector3 = target_food_pos - global_position
	food_distance = delta_pos.length()
	
	var to_food_horiz := Vector2(delta_pos.x, delta_pos.z)
	var horiz_dist: float = to_food_horiz.length()
	
	# Desired target yaw angle to face the food (Godot -Z is forward, +X is right)
	var target_yaw: float = atan2(-delta_pos.x, -delta_pos.z) if horiz_dist > 0.05 else rotation.y
	var yaw_err: float = DualRingAttractor.ang_dist(target_yaw, rotation.y)
	current_yaw_err = yaw_err
	
	# Target pitch angle in 3D (positive = climb/pitch up, negative = dive/pitch down)
	var target_pitch: float = atan2(delta_pos.y, max(horiz_dist, 0.1))
	target_pitch = clamp(target_pitch, -1.05, 1.05)
	
	# State transition:
	# Within 48m or when detecting significant odor, execute SURGE homing
	# Outside plume (> 48m), execute active CAST wide-area exploration
	if odor_strength > ODOR_DETECTION_THRESH or food_distance < 48.0:
		nav_state = AutoNavState.SURGE
		_plume_loss_timer = 0.0
		_last_valid_plume_heading = decoded_heading
	else:
		_plume_loss_timer += delta
		nav_state = AutoNavState.CAST
			
	match nav_state:
		AutoNavState.SURGE:
			# If food is behind (|yaw_err| > 1.1 rad ~ 63 deg), execute sharp turn on spot!
			if abs(yaw_err) > 1.1:
				var turn_dir: float = sign(yaw_err)
				if abs(yaw_err) > 3.1:
					turn_dir = 1.0 # Default clockwise if directly behind
				steer_omega = turn_dir * 5.2
			else:
				# Proportional tracking toward food with crisp CANN steering authority
				steer_omega = clamp(yaw_err * 4.8, -4.8, 4.8)
				
			# Alignment factor: 1.0 when facing food, 0.0 when perpendicular or behind
			var alignment: float = clamp(cos(yaw_err), 0.0, 1.0)
			
			# Pitch directly toward food elevation, modulated by alignment
			var desired_pitch: float = target_pitch * alignment
			rotation.x = lerp(rotation.x, desired_pitch, delta * 8.0)
			
			# Modulate forward throttle by alignment and distance:
			# Surge forward at full speed when aligned; decelerate smoothly within 3m for clean capture
			var approach_factor: float = clamp(food_distance / 3.0, 0.45, 1.0)
			forward_input = lerp(0.15, 1.0, alignment * alignment) * approach_factor
			
			# Vertical climb / dive toward food elevation
			var vert_err: float = delta_pos.y
			vertical_input = clamp(vert_err * 1.6, -1.0, 1.0) * alignment
			
		AutoNavState.CAST:
			_cast_timer += delta
			if _cast_timer >= _cast_duration:
				_cast_timer = 0.0
				_cast_direction *= -1.0
			
			# Boundary Containment: turn back inward if nearing arena edges
			var fly_pos_2d := Vector2(global_position.x, global_position.z)
			if fly_pos_2d.length() > 28.0 or global_position.y < 4.0 or global_position.y > 28.0:
				var to_center := -fly_pos_2d.normalized()
				var desired_heading: float = atan2(-to_center.x, -to_center.y)
				steer_omega = clamp(DualRingAttractor.ang_dist(desired_heading, rotation.y) * 3.0, -2.8, 2.8)
				vertical_input = clamp((14.0 - global_position.y) * 0.25, -0.6, 0.6)
				rotation.x = lerp(rotation.x, vertical_input * 0.35, delta * 5.0)
				forward_input = 0.85
			else:
				# Active crosswind sweeping with forward exploration across the arena volume
				steer_omega = _cast_direction * 1.2
				var target_wave_alt: float = 14.0 + sin(_cast_timer * 1.5) * 6.0
				vertical_input = clamp((target_wave_alt - global_position.y) * 0.25, -0.6, 0.6)
				rotation.x = lerp(rotation.x, vertical_input * 0.35, delta * 5.0)
				forward_input = 0.85
				
		AutoNavState.MENOTAXIS:
			forward_input = 0.60
			vertical_input = clamp((12.0 - global_position.y) * 0.15, -0.4, 0.4)
			steer_omega = 0.0

func _apply_neural_steering(delta: float) -> void:
	# Yaw Rotation
	var target_yaw_rate: float = steer_omega
	var gyro_damping: float = -_current_yaw_rate * (haltere_damping * 0.35)
	_current_yaw_rate = lerp(_current_yaw_rate, target_yaw_rate + gyro_damping * delta, delta * 16.0)
	rotate_y(_current_yaw_rate * delta)
	
	# Wing stroke asymmetry visual feedback
	if abs(steer_omega) > 0.1:
		if steer_omega > 0.0:
			_left_wing_amp = 0.28
			_right_wing_amp = 0.16
		else:
			_left_wing_amp = 0.16
			_right_wing_amp = 0.28
	else:
		_left_wing_amp = lerp(_left_wing_amp, 0.22, delta * 8.0)
		_right_wing_amp = lerp(_right_wing_amp, 0.22, delta * 8.0)
		
	# Coordinated Aerodynamic Banking Roll
	var target_roll: float = -_current_yaw_rate * 0.15 + roll_input * 0.40
	rotation.z = lerp(rotation.z, target_roll, delta * 8.0)

func _integrate_3d_flight(delta: float) -> void:
	var forward_dir: Vector3 = -global_transform.basis.z
	var up_dir: Vector3 = Vector3.UP
	
	var target_vel := Vector3.ZERO
	
	if mode == FlightMode.MANUAL:
		# Direct, responsive vertical climb / dive:
		if abs(vertical_input) > 0.05:
			target_vel += up_dir * (vertical_input * climb_speed)
			
		# Direct forward flight along current heading:
		if abs(forward_input) > 0.05:
			target_vel += forward_dir * (forward_input * max_airspeed)
		else:
			# Gentle idle forward hover drift
			target_vel += forward_dir * 1.0
			
		var active_speed: float = max(abs(forward_input), abs(vertical_input))
		throttle = move_toward(throttle, max(0.35, active_speed * 0.85), delta * 2.0)
		
		# Smooth natural pitch tilt during climb/dive
		var target_pitch: float = 0.0
		if abs(vertical_input) > 0.05:
			target_pitch = vertical_input * 0.45
		elif abs(forward_input) > 0.05:
			target_pitch = 0.08
		rotation.x = lerp(rotation.x, target_pitch, delta * 6.5)
		
	else:
		# Auto mode:
		# Terminal intercept zone: when within 2.2m of target and generally facing it,
		# guide velocity directly into the nutrient orb for a guaranteed, crisp capture!
		if food_distance < 2.2 and abs(current_yaw_err) < 1.0:
			var to_target: Vector3 = target_food_pos - global_position
			var terminal_speed: float = clamp(to_target.length() * 4.0, 2.2, max_airspeed)
			target_vel = to_target.normalized() * terminal_speed
			throttle = 0.55
		else:
			var fwd_speed: float = forward_input * max_airspeed
			var vert_speed: float = vertical_input * climb_speed
			target_vel = forward_dir * fwd_speed + up_dir * vert_speed
			throttle = move_toward(throttle, clamp(forward_input, 0.35, 0.85), delta * 2.0)
	
	# Smoothly interpolate velocity with crisp aerodynamic acceleration
	velocity = velocity.lerp(target_vel, delta * acceleration)
