class_name MacroTabletop
extends Node3D

## Volumetric 3D Grid Arena Environment
## Expansive 80m x 40m x 80m dark grid space with procedural boundary cage,
## free-floating colorful nutrient food source, and 3D volumetric odor plume.

@onready var food_piece: FoodPiece = $FoodPiece
@onready var odor_field: VolumetricOdorField = $VolumetricOdorField

func _ready() -> void:
	_create_boundary_cage()
	
	if food_piece and odor_field:
		food_piece.food_consumed.connect(_on_food_consumed)
		odor_field.set_food_position(food_piece.position)

func _on_food_consumed(new_pos: Vector3) -> void:
	if odor_field:
		odor_field.set_food_position(new_pos)

func _create_boundary_cage() -> void:
	var cage_node := Node3D.new()
	cage_node.name = "BoundaryCage"
	add_child(cage_node)
	
	var line_mat := StandardMaterial3D.new()
	line_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	line_mat.albedo_color = Color(0.22, 0.25, 0.30, 0.6)
	line_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	
	# Bounding box corners (-40 to 40 in X/Z, 0 to 36 in Y)
	var x_min: float = -40.0
	var x_max: float = 40.0
	var y_min: float = 0.0
	var y_max: float = 36.0
	var z_min: float = -40.0
	var z_max: float = 40.0
	
	var edges := [
		# Bottom perimeter
		[Vector3(x_min, y_min, z_min), Vector3(x_max, y_min, z_min)],
		[Vector3(x_max, y_min, z_min), Vector3(x_max, y_min, z_max)],
		[Vector3(x_max, y_min, z_max), Vector3(x_min, y_min, z_max)],
		[Vector3(x_min, y_min, z_max), Vector3(x_min, y_min, z_min)],
		# Top perimeter
		[Vector3(x_min, y_max, z_min), Vector3(x_max, y_max, z_min)],
		[Vector3(x_max, y_max, z_min), Vector3(x_max, y_max, z_max)],
		[Vector3(x_max, y_max, z_max), Vector3(x_min, y_max, z_max)],
		[Vector3(x_min, y_max, z_max), Vector3(x_min, y_max, z_min)],
		# 4 vertical pillars
		[Vector3(x_min, y_min, z_min), Vector3(x_min, y_max, z_min)],
		[Vector3(x_max, y_min, z_min), Vector3(x_max, y_max, z_min)],
		[Vector3(x_max, y_min, z_max), Vector3(x_max, y_max, z_max)],
		[Vector3(x_min, y_min, z_max), Vector3(x_min, y_max, z_max)],
	]
	
	var im := ImmediateMesh.new()
	im.surface_begin(Mesh.PRIMITIVE_LINES, line_mat)
	for edge in edges:
		im.surface_add_vertex(edge[0])
		im.surface_add_vertex(edge[1])
	im.surface_end()
	
	var cage_mesh := MeshInstance3D.new()
	cage_mesh.name = "CageWireframe"
	cage_mesh.mesh = im
	cage_node.add_child(cage_mesh)
