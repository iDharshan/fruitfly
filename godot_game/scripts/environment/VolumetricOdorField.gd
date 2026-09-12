class_name VolumetricOdorField
extends Node3D

## 3D Volumetric Odor Field System
## Simulates realistic turbulent odor dispersion plumes from food sources.
## Couples analytical 3D Gaussian plume physics with FogVolume participating media
## and GPU aerosol particle filaments.

@export var food_position: Vector3 = Vector3(1.2, 0.15, -0.8)
@export var plume_radius: float = 2.5
@export var peak_concentration: float = 1.0
@export var turbulence_intensity: float = 0.18

var _fog_volume: FogVolume
var _particles: GPUParticles3D

func _ready() -> void:
	_setup_volumetric_fog()
	_setup_particles()

func _setup_volumetric_fog() -> void:
	_fog_volume = FogVolume.new()
	_fog_volume.name = "OdorFogVolume"
	_fog_volume.size = Vector3(plume_radius * 2.2, 1.8, plume_radius * 2.2)
	_fog_volume.position = food_position + Vector3(0, 0.4, 0)
	
	var mat := FogMaterial.new()
	mat.density = 0.12
	mat.albedo = Color(0.28, 0.88, 0.48, 1.0) # Emerald nutrient scent hue
	mat.emission = Color(0.04, 0.15, 0.08, 1.0)
	mat.edge_fade = 0.65
	_fog_volume.material = mat
	add_child(_fog_volume)

func _setup_particles() -> void:
	_particles = GPUParticles3D.new()
	_particles.name = "OdorFilamentParticles"
	_particles.position = food_position + Vector3(0, 0.1, 0)
	_particles.amount = 48
	_particles.lifetime = 3.5
	_particles.explosiveness = 0.0
	_particles.randomness = 0.4
	
	var p_mat := ParticleProcessMaterial.new()
	p_mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	p_mat.emission_sphere_radius = 0.35
	p_mat.direction = Vector3(0.2, 1.0, -0.1).normalized() # Gentle upward thermal drift
	p_mat.initial_velocity_min = 0.08
	p_mat.initial_velocity_max = 0.22
	p_mat.gravity = Vector3(0.0, 0.02, 0.0) # Subtle rising buoyancy
	p_mat.scale_min = 0.02
	p_mat.scale_max = 0.06
	p_mat.color = Color(0.35, 0.95, 0.55, 0.45)
	_particles.process_material = p_mat
	
	var quad := QuadMesh.new()
	quad.size = Vector2(0.05, 0.05)
	var quad_mat := StandardMaterial3D.new()
	quad_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	quad_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	quad_mat.albedo_color = Color(0.4, 0.95, 0.6, 0.5)
	quad_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	quad.material = quad_mat
	_particles.draw_pass_1 = quad
	
	add_child(_particles)

## Returns odor concentration in [0.0, 1.0] at any 3D coordinate
func sample_concentration(pos: Vector3) -> float:
	var delta_pos: Vector3 = pos - food_position
	var dist_sq: float = delta_pos.length_squared()
	var two_sigma_sq: float = 2.0 * (plume_radius * plume_radius * 0.25)
	
	var base_conc: float = peak_concentration * exp(-dist_sq / two_sigma_sq)
	
	# Analytical turbulent filament perturbation
	var turb: float = 1.0 + turbulence_intensity * (sin(pos.x * 4.0) * cos(pos.z * 4.0) + sin(pos.y * 6.0))
	return clamp(base_conc * turb, 0.0, 1.0)

## Computes spatial gradient vector pointing toward increasing odor concentration
func sample_gradient(pos: Vector3, eps: float = 0.05) -> Vector3:
	var c_center: float = sample_concentration(pos)
	var grad := Vector3(
		(sample_concentration(pos + Vector3(eps, 0, 0)) - c_center) / eps,
		(sample_concentration(pos + Vector3(0, eps, 0)) - c_center) / eps,
		(sample_concentration(pos + Vector3(0, 0, eps)) - c_center) / eps
	)
	return grad

## Bilateral antenna sampling: returns relative bearing (psi) and concentration
func sample_antennae(fly_pos: Vector3, fly_basis: Basis) -> Dictionary:
	var left_antenna_pos: Vector3 = fly_pos + fly_basis * Vector3(-0.06, 0.05, -0.42)
	var right_antenna_pos: Vector3 = fly_pos + fly_basis * Vector3(0.06, 0.05, -0.42)
	
	var c_left: float = sample_concentration(left_antenna_pos)
	var c_right: float = sample_concentration(right_antenna_pos)
	var c_avg: float = (c_left + c_right) * 0.5
	
	# Vector to food in fly's local frame
	var to_food_world: Vector3 = (food_position - fly_pos).normalized()
	var forward: Vector3 = -fly_basis.z.normalized()
	var right: Vector3 = fly_basis.x.normalized()
	
	# Compute horizontal bearing angle relative to fly's heading:
	# Positive = food is to the right, Negative = food is to the left
	var f_dot: float = forward.dot(to_food_world)
	var r_dot: float = right.dot(to_food_world)
	var relative_bearing: float = atan2(r_dot, f_dot)
	
	return {
		"concentration": c_avg,
		"c_left": c_left,
		"c_right": c_right,
		"relative_bearing": relative_bearing,
		"distance": fly_pos.distance_to(food_position)
	}

func set_food_position(new_pos: Vector3) -> void:
	food_position = new_pos
	if _fog_volume:
		_fog_volume.position = food_position + Vector3(0, 0.4, 0)
	if _particles:
		_particles.position = food_position + Vector3(0, 0.1, 0)
