class_name SunBeacon
extends Node3D

## Celestial Sun Compass Beacon
## Represents the solar navigational reference cue.
## Provides allocentric azimuth angle, directional illumination, and renders
## a golden retinotopic guidance ray connecting to the fly's compound eyes.

@export var is_active: bool = true
@export var orbit_radius: float = 6.0
@export var orbit_height: float = 4.5
@export var sun_angle: float = 0.785 # 45 degrees NE default
@export var target_fly: Node3D = null

var _sun_mesh: MeshInstance3D
var _sun_light: OmniLight3D
var _guidance_beam: ImmediateMesh
var _beam_inst: MeshInstance3D
var _beam_mat: StandardMaterial3D
var _pulse_phase: float = 0.0

func _ready() -> void:
	_build_sun_orb()
	_setup_guidance_beam()
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
	mat.albedo_color = Color(1.0, 0.95, 0.65)
	_sun_mesh.material_override = mat
	add_child(_sun_mesh)
	
	# Local omni light for celestial glow
	_sun_light = OmniLight3D.new()
	_sun_light.name = "SunPointLight"
	_sun_light.light_color = Color(1.0, 0.94, 0.82)
	_sun_light.light_energy = 3.5
	_sun_light.omni_range = 15.0
	_sun_light.omni_attenuation = 1.2
	add_child(_sun_light)

func _setup_guidance_beam() -> void:
	_guidance_beam = ImmediateMesh.new()
	_beam_inst = MeshInstance3D.new()
	_beam_inst.name = "GuidanceBeam"
	_beam_inst.mesh = _guidance_beam
	_beam_inst.top_level = true # Draw in global world coordinates
	
	_beam_mat = StandardMaterial3D.new()
	_beam_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	_beam_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_beam_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_beam_mat.albedo_color = Color(1.0, 0.88, 0.35, 0.45)
	_beam_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_beam_inst.material_override = _beam_mat
	
	add_child(_beam_inst)

func _process(delta: float) -> void:
	_pulse_phase = fmod(_pulse_phase + delta * 3.5, TAU)
	_update_guidance_beam()

func _update_guidance_beam() -> void:
	if not _guidance_beam or not _beam_inst:
		return
		
	_guidance_beam.clear_surfaces()
	
	if not is_active or not is_instance_valid(target_fly):
		_beam_inst.visible = false
		return
		
	_beam_inst.visible = true
	var p_sun: Vector3 = global_position
	var p_fly: Vector3 = target_fly.global_position + target_fly.global_transform.basis * Vector3(0.0, 0.05, -0.32)
	
	var pulse_alpha: float = 0.30 + 0.18 * sin(_pulse_phase)
	_beam_mat.albedo_color = Color(1.0, 0.86, 0.35, pulse_alpha)
	
	# Draw dual retinotopic beam lines (to left and right compound eyes)
	var left_eye_pos: Vector3 = target_fly.global_position + target_fly.global_transform.basis * Vector3(-0.08, 0.06, -0.34)
	var right_eye_pos: Vector3 = target_fly.global_position + target_fly.global_transform.basis * Vector3(0.08, 0.06, -0.34)
	
	_guidance_beam.surface_begin(Mesh.PRIMITIVE_LINES, _beam_mat)
	# Central primary ray
	_guidance_beam.surface_add_vertex(p_sun)
	_guidance_beam.surface_add_vertex(p_fly)
	# Left ommatidia ray
	_guidance_beam.surface_add_vertex(p_sun)
	_guidance_beam.surface_add_vertex(left_eye_pos)
	# Right ommatidia ray
	_guidance_beam.surface_add_vertex(p_sun)
	_guidance_beam.surface_add_vertex(right_eye_pos)
	_guidance_beam.surface_end()

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
	if _beam_inst:
		_beam_inst.visible = is_active
	print("Sun Beacon active state: ", is_active)
