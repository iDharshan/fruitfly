class_name FlightCameraController
extends Camera3D

## Dynamic Multi-View Cinematic Camera Controller
## Supports 4 Distinct Camera Perspectives:
##   1. CHASE Cam: 3rd-person cinematic follow with spring-arm obstacle avoidance and banking
##   2. FPV Cam: Compound eye cockpit vision with hexagonal chromatic dispersion filter
##   3. ORBIT (Macro Free Cam): 360-deg free orbit around fly with cuticle / wing shader inspection
##   4. SPLIT (Split Telemetry View): Flight viewport side-by-side with full connectome inspection
##
## Cycling Controls: 'C' key or 'TAB', or directly via numbers '1', '2', '3', '4'.

enum CameraMode { CHASE = 0, FPV = 1, ORBIT = 2, SPLIT = 3 }

@export var target_agent: FlyAgent
@export var current_mode: CameraMode = CameraMode.CHASE
@export var follow_smoothness: float = 8.5
@export var spring_arm_radius: float = 0.08 # Collision sphere radius
@export var default_chase_offset: Vector3 = Vector3(0, 0.45, 1.35)

# Orbit Camera State
var _orbit_pitch: float = -12.0
var _orbit_yaw: float = 0.0
var _orbit_distance: float = 1.85
var _is_right_dragging: bool = false
var _last_mouse_pos: Vector2 = Vector2.ZERO

# Damped Follow State
var _damped_forward: Vector3 = Vector3.FORWARD
var _damped_up: Vector3 = Vector3.UP
var _current_fpv_fade: float = 0.0

signal camera_mode_changed(new_mode: CameraMode)
signal fpv_intensity_changed(intensity: float)

func _ready() -> void:
	if is_instance_valid(target_agent):
		_damped_forward = -target_agent.global_transform.basis.z
		_damped_up = target_agent.global_transform.basis.y

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_camera"):
		_cycle_camera_mode()
	elif event.is_action_pressed("toggle_cockpit"):
		# Toggle between CHASE and SPLIT or FPV
		if current_mode == CameraMode.CHASE:
			set_camera_mode(CameraMode.SPLIT)
		elif current_mode == CameraMode.SPLIT:
			set_camera_mode(CameraMode.FPV)
		else:
			set_camera_mode(CameraMode.CHASE)
	elif event is InputEventKey and event.pressed:
		if event.keycode == KEY_1:
			set_camera_mode(CameraMode.CHASE)
		elif event.keycode == KEY_2:
			set_camera_mode(CameraMode.FPV)
		elif event.keycode == KEY_3:
			set_camera_mode(CameraMode.ORBIT)
		elif event.keycode == KEY_4:
			set_camera_mode(CameraMode.SPLIT)

	# Right click drag for Free Orbit Mode
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			_is_right_dragging = event.pressed
			_last_mouse_pos = event.position
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and current_mode == CameraMode.ORBIT:
			_orbit_distance = clamp(_orbit_distance - 0.15, 0.4, 4.5)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and current_mode == CameraMode.ORBIT:
			_orbit_distance = clamp(_orbit_distance + 0.15, 0.4, 4.5)

	elif event is InputEventMouseMotion and _is_right_dragging:
		var delta_mouse: Vector2 = event.position - _last_mouse_pos
		_last_mouse_pos = event.position
		_orbit_yaw -= delta_mouse.x * 0.35
		_orbit_pitch = clamp(_orbit_pitch - delta_mouse.y * 0.35, -78.0, 78.0)

func _cycle_camera_mode() -> void:
	var next_mode = ((int(current_mode) + 1) % 4) as CameraMode
	set_camera_mode(next_mode)

func set_camera_mode(mode: CameraMode) -> void:
	current_mode = mode
	print("Active Camera Mode: ", CameraMode.keys()[current_mode])
	camera_mode_changed.emit(current_mode)

func _physics_process(delta: float) -> void:
	if not is_instance_valid(target_agent):
		return

	# Smoothly transition FPV shader intensity
	var target_fpv: float = 1.0 if current_mode == CameraMode.FPV else 0.0
	_current_fpv_fade = move_toward(_current_fpv_fade, target_fpv, delta * 5.0)
	fpv_intensity_changed.emit(_current_fpv_fade)

	match current_mode:
		CameraMode.CHASE, CameraMode.SPLIT:
			_process_chase_camera(delta)

		CameraMode.FPV:
			_process_fpv_camera(delta)

		CameraMode.ORBIT:
			_process_orbit_camera(delta)

func _process_chase_camera(delta: float) -> void:
	var agent_pos: Vector3 = target_agent.global_position
	var look_target: Vector3 = agent_pos + Vector3(0, 0.08, 0)

	# Smoothly track agent orientation
	var agent_forward: Vector3 = -target_agent.global_transform.basis.z
	var agent_up: Vector3 = target_agent.global_transform.basis.y
	_damped_forward = _damped_forward.slerp(agent_forward, delta * follow_smoothness)
	_damped_up = _damped_up.slerp(agent_up, delta * follow_smoothness * 0.8)

	# Ideal chase camera position in local flight space
	var ideal_offset: Vector3 = -_damped_forward * default_chase_offset.z + _damped_up * default_chase_offset.y
	var ideal_pos: Vector3 = agent_pos + ideal_offset

	# Spring-arm Obstacle Avoidance via SphereCast
	var final_pos: Vector3 = _resolve_spring_arm_collision(agent_pos, ideal_pos)
	global_position = global_position.lerp(final_pos, delta * follow_smoothness)

	look_at(look_target, _damped_up)

func _process_fpv_camera(delta: float) -> void:
	var mount: Marker3D = target_agent.cockpit_cam_mount
	if mount:
		global_transform = mount.global_transform
	else:
		# Fallback to anterior fly head position
		var head_pos: Vector3 = target_agent.global_position - target_agent.global_transform.basis.z * 0.12 + target_agent.global_transform.basis.y * 0.04
		global_position = head_pos
		look_at(head_pos - target_agent.global_transform.basis.z, target_agent.global_transform.basis.y)

func _process_orbit_camera(delta: float) -> void:
	var center: Vector3 = target_agent.global_position + Vector3(0, 0.04, 0)
	var yaw_rad: float = deg_to_rad(_orbit_yaw)
	var pitch_rad: float = deg_to_rad(_orbit_pitch)

	var offset := Vector3(
		_orbit_distance * cos(pitch_rad) * sin(yaw_rad),
		-_orbit_distance * sin(pitch_rad),
		_orbit_distance * cos(pitch_rad) * cos(yaw_rad)
	)
	var target_pos: Vector3 = center + offset
	global_position = global_position.lerp(target_pos, delta * 12.0)
	look_at(center, Vector3.UP)

func _resolve_spring_arm_collision(from_pos: Vector3, to_pos: Vector3) -> Vector3:
	var space_state = get_world_3d().direct_space_state
	if not space_state:
		return to_pos

	var query := PhysicsRayQueryParameters3D.create(from_pos, to_pos)
	query.exclude = [target_agent.get_rid()]
	var result: Dictionary = space_state.intersect_ray(query)

	if not result.is_empty():
		var hit_pos: Vector3 = result.get("position", to_pos)
		var hit_normal: Vector3 = result.get("normal", Vector3.UP)
		# Pull slightly away from collision obstacle
		return hit_pos + hit_normal * spring_arm_radius

	return to_pos
