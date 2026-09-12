class_name SunBeacon
extends Node3D

## Celestial Sun Compass Beacon
## Represents the solar navigational reference cue.
## Provides allocentric azimuth angle and visual anchor guidance to the fly's E-PG compass.

@export var is_active: bool = true
@export var orbit_radius: float = 6.0
@export var orbit_height: float = 4.5
@export var sun_angle: float = 0.785 # 45 degrees NE default

var _sun_mesh: MeshInstance3D
var _sun_light: DirectionalLight3D
var _guidance_beam: ImmediateMesh
var _beam_inst: MeshInstance3D

func _ready() -> void:
	_build_sun_orb()
	_update_position()

func _build_sun_orb() -> void:
	# 1. Glowing Solar Sphere
	var sphere := SphereMesh.new()
	sphere.radius = 0.45
	sphere.height = 0.90
	
	_sun_mesh = MeshInstance3D.new()
	_sun_mesh.name = "SunOrb"
	_sun_mesh.mesh = sphere
	
	var mat := StandardMaterial3D.new()
	mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(1.0, 0.92, 0.6)
	_sun_mesh.material_override = mat
	add_child(_sun_mesh)

func _update_position() -> void:
	var x: float = orbit_radius * cos(sun_angle)
	var z: float = orbit_radius * sin(sun_angle)
	position = Vector3(x, orbit_height, z)

## Returns the allocentric celestial azimuth angle in [0, 2pi)
func get_sun_azimuth() -> float:
	# Azimuth in horizontal X-Z plane
	var norm_pos := Vector2(position.x, position.z).normalized()
	return fposmod(atan2(norm_pos.y, norm_pos.x), TAU)

func set_sun_angle(new_angle: float) -> void:
	sun_angle = fposmod(new_angle, TAU)
	_update_position()

func toggle_active() -> void:
	is_active = not is_active
	visible = is_active
	print("Sun Beacon active state: ", is_active)
