class_name FlyAgent
extends CharacterBody3D

## Drosophila 3D Fly Agent
## Combines 6-DOF biomechanical flight kinematics, procedural anatomical mesh,
## 200 Hz wing & haltere animation, and real-time audio synthesis.

@export var max_airspeed: float = 3.5 # units / sec (~1.2 m/s biological equivalent)
@export var acceleration: float = 8.0
@export var drag_coefficient: float = 2.5
@export var lift_coefficient: float = 1.8
@export var yaw_sensitivity: float = 3.2
@export var pitch_sensitivity: float = 2.4
@export var roll_sensitivity: float = 2.8

# Animation nodes
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
var throttle: float = 0.0
var target_throttle: float = 0.0
var pitch_input: float = 0.0
var yaw_input: float = 0.0
var roll_input: float = 0.0
var vertical_input: float = 0.0

# Wing Flap State (200 Hz)
var _wing_phase: float = 0.0
var _wing_freq: float = 200.0
var _left_wing_amp: float = 0.22
var _right_wing_amp: float = 0.22

# Camera Mounts
@onready var chase_cam_mount: Marker3D = $ChaseCamMount
@onready var cockpit_cam_mount: Marker3D = $CockpitCamMount

func _ready() -> void:
	# 1. Procedural Drosophila Mesh Generation
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
			
	# 2. Audio Synthesizer Setup
	_audio_buzz = WingAudioSynthesizer.new()
	_audio_buzz.name = "WingAudio"
	add_child(_audio_buzz)

func _process(delta: float) -> void:
	# 200 Hz Wingbeat Phase Integration
	var current_freq: float = lerp(190.0, 240.0, throttle)
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
		
	# Haltere Gyroscopic Antiphase Oscillation (Anti-phase to wings)
	var haltere_swing: float = -cos(_wing_phase) * 0.45
	if _left_haltere_root:
		_left_haltere_root.rotation.x = haltere_swing
	if _right_haltere_root:
		_right_haltere_root.rotation.x = -haltere_swing
		
	# Modulate Audio
	if _audio_buzz:
		_audio_buzz.set_flight_throttle(throttle, true)

func _physics_process(delta: float) -> void:
	# Throttle Damping & Acceleration
	throttle = move_toward(throttle, target_throttle, acceleration * delta * 0.4)
	
	# 6-DOF Aerodynamic Forces
	# Forward direction in Godot standard is -transform.basis.z
	var forward_dir: Vector3 = -global_transform.basis.z
	var up_dir: Vector3 = global_transform.basis.y
	var right_dir: Vector3 = global_transform.basis.x
	
	# Forward Thrust
	var thrust_force: Vector3 = forward_dir * (throttle * max_airspeed)
	
	# Lift & Vertical Control
	var lift_force: Vector3 = up_dir * (vertical_input * lift_coefficient + throttle * 0.5)
	
	# Apply Aerodynamic Drag
	var current_vel: Vector3 = velocity
	var drag_force: Vector3 = -current_vel * drag_coefficient * delta
	
	velocity = velocity.lerp(thrust_force + lift_force, delta * 3.5) + drag_force
	
	# Rotational Torques (Pitch, Yaw, Roll)
	var rot_delta: Vector3 = Vector3.ZERO
	rot_delta.x = pitch_input * pitch_sensitivity * delta
	rot_delta.y = yaw_input * yaw_sensitivity * delta
	rot_delta.z = roll_input * roll_sensitivity * delta
	
	# Natural Banking Roll into Yaw Turns
	var auto_bank: float = -yaw_input * 0.45
	rot_delta.z += (auto_bank - rotation.z) * delta * 4.0
	
	# Apply rotations
	rotate_object_local(Vector3.RIGHT, rot_delta.x)
	rotate_y(rot_delta.y)
	rotate_object_local(Vector3.FORWARD, rot_delta.z)
	
	# Move using Godot CharacterBody3D kinematics
	move_and_slide()
