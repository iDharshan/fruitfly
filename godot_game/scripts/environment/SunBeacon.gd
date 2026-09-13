class_name SunBeacon
extends Node3D

## Celestial Sun Compass Beacon
## Background solar navigational reference cue.
## NOTE: Independent reference - NEVER visually tethered to the fly.

@export var is_active: bool = false
@export var orbit_radius: float = 30.0
@export var orbit_height: float = 22.0
@export var sun_angle: float = 0.785 # 45 degrees NE default
@export var target_fly: Node3D = null

var _sun_mesh: MeshInstance3D
var _sun_light: OmniLight3D
var _beam_inst: MeshInstance3D # Kept for test compatibility, never drawn
var _pulse_phase: float = 0.0

func _ready() -> void:
	_build_sun_orb()
	_setup_dummy_beam()
	_update_position()
	visible = is_active

func _build_sun_orb() -> void:
	var sphere := SphereMesh.new()
	sphere.radius = 0.35
	sphere.height = 0.70
	
	_sun_mesh = MeshInstance3D.new()
	_sun_mesh.name = "SunOrb"
	_sun_mesh.mesh = sphere
	
	var mat := StandardMaterial3D.new()
	mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(1.0, 0.95, 0.75, 0.8)
	_sun_mesh.material_override = mat
	add_child(_sun_mesh)
	
	_sun_light = OmniLight3D.new()
	_sun_light.name = "SunPointLight"
	_sun_light.light_color = Color(1.0, 0.95, 0.85)
	_sun_light.light_energy = 1.5
	_sun_light.omni_range = 25.0
	_sun_light.omni_attenuation = 1.5
	add_child(_sun_light)

func _setup_dummy_beam() -> void:
	_beam_inst = MeshInstance3D.new()
	_beam_inst.name = "GuidanceBeam"
	_beam_inst.visible = false
	add_child(_beam_inst)

func _process(_delta: float) -> void:
	pass

func _update_position() -> void:
	var x: float = orbit_radius * cos(sun_angle)
	var z: float = orbit_radius * sin(sun_angle)
	position = Vector3(x, orbit_height, z)

## Returns the allocentric celestial azimuth angle in [0, 2pi)
func get_sun_azimuth() -> float:
	var norm_pos := Vector2(position.x, position.z).normalized()
	return fposmod(atan2(norm_pos.y, norm_pos.x), TAU)

func set_sun_angle(new_angle: float) -> void:
	sun_angle = fposmod(new_angle, TAU)
	_update_position()

func toggle_active() -> void:
	is_active = not is_active
	visible = is_active
	print("Sun Beacon active state: ", is_active)
