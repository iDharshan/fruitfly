class_name FlightCameraController
extends Camera3D

## Dynamic Multi-View Camera Controller
## Supports Chase Cam, Compound Eye FPV, and Macro Orbit Inspection modes.
## Toggle with 'C' key.

enum CameraMode { CHASE, FPV, ORBIT }

@export var target_agent: FlyAgent
@export var current_mode: CameraMode = CameraMode.CHASE
@export var follow_smoothness: float = 8.0

var _orbit_pitch: float = -15.0
var _orbit_yaw: float = 0.0
var _orbit_distance: float = 2.0

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_camera"):
		_cycle_camera_mode()
	elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		_orbit_yaw -= event.relative.x * 0.3
		_orbit_pitch = clamp(_orbit_pitch - event.relative.y * 0.3, -80.0, 80.0)

func _cycle_camera_mode() -> void:
	current_mode = (current_mode + 1) % 3 as CameraMode
	print("Camera mode switched to: ", CameraMode.keys()[current_mode])

func _physics_process(delta: float) -> void:
	if not is_instance_valid(target_agent):
		return
		
	match current_mode:
		CameraMode.CHASE:
			# Smooth follow behind ChaseCamMount
			var mount: Marker3D = target_agent.chase_cam_mount
			if mount:
				var target_pos: Vector3 = mount.global_position
				global_position = global_position.lerp(target_pos, delta * follow_smoothness)
				var look_target: Vector3 = target_agent.global_position + Vector3(0, 0.08, 0)
				look_at(look_target, Vector3.UP)
		
		CameraMode.FPV:
			# Lock directly to CockpitCamMount
			var mount: Marker3D = target_agent.cockpit_cam_mount
			if mount:
				global_transform = mount.global_transform
		
		CameraMode.ORBIT:
			# Orbit around fly center
			var center: Vector3 = target_agent.global_position
			var yaw_rad: float = deg_to_rad(_orbit_yaw)
			var pitch_rad: float = deg_to_rad(_orbit_pitch)
			
			var offset := Vector3(
				_orbit_distance * cos(pitch_rad) * sin(yaw_rad),
				-_orbit_distance * sin(pitch_rad),
				_orbit_distance * cos(pitch_rad) * cos(yaw_rad)
			)
			global_position = center + offset
			look_at(center, Vector3.UP)
