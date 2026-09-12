class_name MacroTabletop
extends Node3D

## Macro Tabletop Environment Builder
## Constructs the rustic wooden kitchen countertop, boundary collision walls,
## surface-tension water droplets, decaying fruit piece, and 3D volumetric odor field.

const WATER_SHADER_PATH = "res://shaders/water_droplet.gdshader"

@onready var food_piece: FoodPiece = $FoodPiece
@onready var odor_field: VolumetricOdorField = $VolumetricOdorField

func _ready() -> void:
	_create_water_droplets()
	
	if food_piece and odor_field:
		food_piece.food_consumed.connect(_on_food_consumed)
		odor_field.set_food_position(food_piece.position)

func _on_food_consumed(new_pos: Vector3) -> void:
	if odor_field:
		odor_field.set_food_position(new_pos)

func _create_water_droplets() -> void:
	var water_shader: Shader = load(WATER_SHADER_PATH)
	var droplet_mat := ShaderMaterial.new()
	droplet_mat.shader = water_shader
	
	var droplet_positions := [
		Vector3(-0.8, 0.02, 0.6),
		Vector3(-0.85, 0.015, 0.72),
		Vector3(0.5, 0.025, 0.8),
		Vector3(1.1, 0.02, 0.4),
		Vector3(-0.4, 0.018, -1.1),
		Vector3(0.8, 0.022, -1.2),
	]
	
	for i in range(droplet_positions.size()):
		var pos: Vector3 = droplet_positions[i]
		var drop_mesh := SphereMesh.new()
		var radius: float = randf_range(0.06, 0.12)
		drop_mesh.radius = radius
		drop_mesh.height = radius * 0.9 # Flattened convex lens by surface tension
		
		var inst := MeshInstance3D.new()
		inst.name = "WaterDrop_" + str(i)
		inst.mesh = drop_mesh
		inst.position = pos
		inst.material_override = droplet_mat
		add_child(inst)
