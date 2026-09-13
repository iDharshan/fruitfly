class_name VolumetricOdorField
extends Node3D

## 3D Volumetric Odor Field System
## Simulates isotropic and wind-advected 3D odor plumes in the full arena space.
## Provides high-fidelity 3D antenna sensing: bilateral concentration,
## 3D relative bearing (azimuth), and 3D relative elevation (pitch).

const ODOR_FOG_SHADER_PATH = "res://shaders/odor_fog.gdshader"

@export var food_position: Vector3 = Vector3(0.0, 8.0, -10.0)
@export var plume_radius: float = 24.0
@export var peak_concentration: float = 1.0
@export var turbulence_intensity: float = 0.12
@export var ambient_wind: Vector3 = Vector3(0.15, 0.0, -0.10)

var _fog_volume: FogVolume
var _particles: GPUParticles3D
var _fog_mat: ShaderMaterial

func _ready() -> void:
	_setup_volumetric_fog()
	_setup_particles()

func _setup_volumetric_fog() -> void:
	_fog_volume = FogVolume.new()
	_fog_volume.name = "OdorFogVolume"
	_fog_volume.size = Vector3(plume_radius * 2.0, plume_radius * 2.0, plume_radius * 2.0)
	_fog_volume.position = food_position
	
	var shader: Shader = load(ODOR_FOG_SHADER_PATH)
	if shader:
		_fog_mat = ShaderMaterial.new()
		_fog_mat.shader = shader
		_fog_mat.set_shader_parameter("odor_color", Color(0.25, 0.95, 0.55))
		_fog_mat.set_shader_parameter("odor_emission", Color(0.04, 0.18, 0.08))
		_fog_mat.set_shader_parameter("base_density", 0.16)
		_fog_mat.set_shader_parameter("turbulence_scale", 2.0)
		_fog_volume.material = _fog_mat
	else:
		var fallback_mat := FogMaterial.new()
		fallback_mat.density = 0.10
		fallback_mat.albedo = Color(0.25, 0.90, 0.50, 1.0)
		fallback_mat.emission = Color(0.04, 0.15, 0.08, 1.0)
		fallback_mat.edge_fade = 0.8
		_fog_volume.material = fallback_mat
		
	add_child(_fog_volume)

func _setup_particles() -> void:
	_particles = GPUParticles3D.new()
	_particles.name = "OdorFilamentParticles"
	_particles.position = food_position
	_particles.amount = 48
	_particles.lifetime = 3.0
	_particles.explosiveness = 0.0
	_particles.randomness = 0.5
	
	var p_mat := ParticleProcessMaterial.new()
	p_mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	p_mat.emission_sphere_radius = 0.8
	var drift_dir: Vector3 = (ambient_wind.normalized() * 0.6 + Vector3.UP * 0.4).normalized()
	p_mat.direction = drift_dir
	p_mat.initial_velocity_min = 0.12
	p_mat.initial_velocity_max = 0.35
	p_mat.gravity = Vector3(ambient_wind.x * 0.08, 0.02, ambient_wind.z * 0.08)
	p_mat.scale_min = 0.03
	p_mat.scale_max = 0.08
	p_mat.color = Color(0.35, 0.98, 0.60, 0.40)
	_particles.process_material = p_mat
	
	var quad := QuadMesh.new()
	quad.size = Vector2(0.06, 0.06)
	var quad_mat := StandardMaterial3D.new()
	quad_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	quad_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	quad_mat.albedo_color = Color(0.35, 0.98, 0.60, 0.40)
	quad_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	quad.material = quad_mat
	_particles.draw_pass_1 = quad
	
	add_child(_particles)

## Returns 3D odor concentration in [0.0, 1.0] taking into account 3D distance and wind advection
func sample_concentration(pos: Vector3) -> float:
	var delta_pos: Vector3 = pos - food_position
	var dist: float = delta_pos.length()
	var wind_speed: float = ambient_wind.length()
	var wind_bias: float = 1.0
	if wind_speed > 0.01 and dist > 0.01:
		var wind_dir: Vector3 = ambient_wind.normalized()
		var cos_wind: float = delta_pos.normalized().dot(wind_dir)
		wind_bias = 1.0 - 0.35 * cos_wind
		
	var effective_dist: float = dist * wind_bias
	var two_sigma_sq: float = 2.0 * (plume_radius * plume_radius * 0.30)
	var base_conc: float = peak_concentration * exp(-(effective_dist * effective_dist) / two_sigma_sq)
	var turb: float = 1.0 + turbulence_intensity * (sin(pos.x * 2.0) * cos(pos.z * 2.0) + sin(pos.y * 3.0))
	return clamp(base_conc * turb, 0.0, 1.0)

## Computes 3D spatial gradient vector pointing toward increasing odor concentration
func sample_gradient(pos: Vector3, eps: float = 0.1) -> Vector3:
	var c_center: float = sample_concentration(pos)
	var grad := Vector3(
		(sample_concentration(pos + Vector3(eps, 0, 0)) - c_center) / eps,
		(sample_concentration(pos + Vector3(0, eps, 0)) - c_center) / eps,
		(sample_concentration(pos + Vector3(0, 0, eps)) - c_center) / eps
	)
	return grad

## Full 3D bilateral antenna sampling
func sample_antennae(fly_pos: Vector3, fly_basis: Basis) -> Dictionary:
	# Scaled antenna positions matching small slender fly geometry
	var left_antenna_pos: Vector3 = fly_pos + fly_basis * Vector3(-0.02, 0.02, -0.19)
	var right_antenna_pos: Vector3 = fly_pos + fly_basis * Vector3(0.02, 0.02, -0.19)
	
	var c_left: float = sample_concentration(left_antenna_pos)
	var c_right: float = sample_concentration(right_antenna_pos)
	var c_avg: float = (c_left + c_right) * 0.5
	
	# Vector to food in world space
	var delta_world: Vector3 = food_position - fly_pos
	var dist_3d: float = delta_world.length()
	var dir_world: Vector3 = delta_world / max(dist_3d, 0.001)
	
	# Transform into fly's local coordinate system:
	# -basis.z is Forward, basis.x is Right, basis.y is Up
	var forward: Vector3 = -fly_basis.z.normalized()
	var right: Vector3 = fly_basis.x.normalized()
	var up: Vector3 = fly_basis.y.normalized()
	
	var f_dot: float = forward.dot(dir_world)
	var r_dot: float = right.dot(dir_world)
	var u_dot: float = up.dot(dir_world)
	
	# Azimuth (horizontal bearing angle: left/right error)
	var relative_bearing: float = atan2(r_dot, f_dot)
	
	# Elevation (vertical pitch angle: up/down error)
	var horiz_proj: float = sqrt(f_dot * f_dot + r_dot * r_dot)
	var relative_elevation: float = atan2(u_dot, horiz_proj)
	
	return {
		"concentration": c_avg,
		"c_left": c_left,
		"c_right": c_right,
		"relative_bearing": relative_bearing,
		"relative_elevation": relative_elevation,
		"distance": dist_3d,
		"vertical_delta": delta_world.y,
		"dir_world": dir_world,
		"food_position": food_position,
		"wind_vector": ambient_wind
	}

func set_food_position(new_pos: Vector3) -> void:
	food_position = new_pos
	if _fog_volume:
		_fog_volume.position = food_position
	if _particles:
		_particles.position = food_position
