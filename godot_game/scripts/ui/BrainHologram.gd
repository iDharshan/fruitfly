class_name BrainHologram
extends Node3D

## 3D Anatomical Drosophila Central Complex Connectome Hologram
## Renders 2,900 morphological nodes and 1,630 structural axonal tracts in full 3D space.
## Nodes glow with real-time neon bioluminescence (0 - 200+ Hz) dynamically matching
## the biological CANN circuit (EB bump, PB shifters, FB sensory grid, PFL3 comparators, VNC cords).
## Features GPU-instanced MultiMesh rendering, traveling action potential spark pulses,
## and interactive 3D orbit / zoom camera controls.

signal camera_moved(yaw_deg: float, pitch_deg: float, zoom: float)

@export var connectome_path: String = "res://assets/data/connectome_1920.json"
@export var auto_rotate: bool = true
@export var rotation_speed: float = 0.25
@export var max_active_pulses: int = 56

# MultiMesh & Geometry Nodes
var _nodes_multimesh: MultiMeshInstance3D
var _tracts_mesh: MeshInstance3D
var _pulses_multimesh: MultiMeshInstance3D
var _root_transform_node: Node3D

# Camera & Interactive Orbit
var camera: Camera3D
var _cam_pivot: Node3D
var _cam_pitch_node: Node3D
var _yaw: float = 0.0
var _pitch: float = 0.22 # Gentle downward perspective angle
var _zoom_distance: float = 2.85
var _is_dragging: bool = false
var _last_mouse_pos: Vector2 = Vector2.ZERO
var _idle_time: float = 0.0

# Morphological Data
var _node_data: Array = []
var _node_positions: PackedVector3Array = PackedVector3Array()
var _node_rates: PackedFloat32Array = PackedFloat32Array()
var _tract_edges: Array = []
var _actionable_edges: Array = []

# Action Potential Pulses
class SynapticPulse:
	var src_pos: Vector3
	var dst_pos: Vector3
	var progress: float = 0.0
	var speed: float = 2.5
	var color: Color = Color.WHITE
	var size: float = 1.0

var _pulses: Array[SynapticPulse] = []
var _pulse_timer: float = 0.0

func _ready() -> void:
	_setup_scene_hierarchy()
	_load_connectome_data()
	_build_multimesh_nodes()
	_build_tract_lines()
	_build_pulses_multimesh()

func _setup_scene_hierarchy() -> void:
	_root_transform_node = Node3D.new()
	_root_transform_node.name = "ConnectomeRoot"
	add_child(_root_transform_node)

	# Camera Rig with smooth pivot
	_cam_pivot = Node3D.new()
	_cam_pivot.name = "CameraPivot"
	_cam_pivot.position = Vector3(0, -0.25, 0) # Pivot around central complex / upper VNC
	add_child(_cam_pivot)

	_cam_pitch_node = Node3D.new()
	_cam_pitch_node.name = "CameraPitch"
	_cam_pivot.add_child(_cam_pitch_node)

	camera = Camera3D.new()
	camera.name = "HologramCamera"
	camera.position = Vector3(0, 0, _zoom_distance)
	camera.current = true
	camera.fov = 42.0
	_cam_pitch_node.add_child(camera)
	
	_update_camera_transform()

func _load_connectome_data() -> void:
	if not FileAccess.file_exists(connectome_path):
		push_error("Connectome JSON not found at: " + connectome_path)
		return

	var file = FileAccess.open(connectome_path, FileAccess.READ)
	var text: String = file.get_as_text()
	var parsed = JSON.parse_string(text)
	if not parsed is Dictionary:
		push_error("Failed to parse connectome JSON")
		return

	_node_data = parsed.get("nodes", [])
	_tract_edges = parsed.get("edges", [])

	var n_count: int = _node_data.size()
	_node_positions.resize(n_count)
	_node_rates.resize(n_count)

	for i in range(n_count):
		var n = _node_data[i]
		_node_positions[i] = Vector3(n.get("x", 0.0), n.get("y", 0.0), n.get("z", 0.0))
		_node_rates[i] = float(n.get("base_rate", 18.0))

	# Index actionable edges for action potential pulse propagation
	for e in _tract_edges:
		var etype: String = e.get("type", "")
		if etype.begins_with("PFL3") or etype.begins_with("VNC") or etype in ["EPG_PB", "EB_RING", "AL_FB", "LAL_VNC", "PB_TRACT"]:
			var src_idx: int = e.get("src", 0)
			var dst_idx: int = e.get("dst", 0)
			if src_idx < n_count and dst_idx < n_count:
				_actionable_edges.append({
					"src": src_idx,
					"dst": dst_idx,
					"type": etype,
					"src_pos": _node_positions[src_idx],
					"dst_pos": _node_positions[dst_idx]
				})

func _build_multimesh_nodes() -> void:
	var n_count: int = _node_data.size()
	if n_count == 0:
		return

	_nodes_multimesh = MultiMeshInstance3D.new()
	_nodes_multimesh.name = "NodesMultiMesh"

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.instance_count = n_count

	var sphere := SphereMesh.new()
	sphere.radius = 0.0125
	sphere.height = 0.025
	sphere.radial_segments = 6
	sphere.rings = 4

	var mat := StandardMaterial3D.new()
	mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	mat.vertex_color_use_as_albedo = true
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_DISABLED
	sphere.material = mat

	mm.mesh = sphere

	for i in range(n_count):
		var pos: Vector3 = _node_positions[i]
		mm.set_instance_transform(i, Transform3D(Basis(), pos))
		mm.set_instance_color(i, Color(0.12, 0.45, 0.65, 0.45))

	_nodes_multimesh.multimesh = mm
	_root_transform_node.add_child(_nodes_multimesh)

func _build_tract_lines() -> void:
	if _tract_edges.is_empty():
		return

	_tracts_mesh = MeshInstance3D.new()
	_tracts_mesh.name = "TractLines"

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_LINES)

	for e in _tract_edges:
		var s_idx: int = e.get("src", 0)
		var d_idx: int = e.get("dst", 0)
		if s_idx >= _node_positions.size() or d_idx >= _node_positions.size():
			continue

		var etype: String = e.get("type", "")
		var tract_col := Color(0.14, 0.32, 0.48, 0.22)
		if etype == "EB_RING" or etype == "EPG_PB":
			tract_col = Color(0.12, 0.55, 0.68, 0.35)
		elif etype.begins_with("PFL3_L"):
			tract_col = Color(0.18, 0.48, 0.78, 0.32)
		elif etype.begins_with("PFL3_R"):
			tract_col = Color(0.78, 0.38, 0.18, 0.32)
		elif etype == "AL_FB":
			tract_col = Color(0.20, 0.65, 0.40, 0.35)
		elif etype.begins_with("VNC"):
			tract_col = Color(0.22, 0.42, 0.62, 0.28)

		st.set_color(tract_col)
		st.add_vertex(_node_positions[s_idx])
		st.set_color(tract_col)
		st.add_vertex(_node_positions[d_idx])

	var line_mesh := st.commit()
	var line_mat := StandardMaterial3D.new()
	line_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	line_mat.vertex_color_use_as_albedo = true
	line_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	line_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_tracts_mesh.mesh = line_mesh
	_tracts_mesh.material_override = line_mat

	_root_transform_node.add_child(_tracts_mesh)

func _build_pulses_multimesh() -> void:
	_pulses_multimesh = MultiMeshInstance3D.new()
	_pulses_multimesh.name = "PulsesMultiMesh"

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.instance_count = max_active_pulses

	var spark_mesh := SphereMesh.new()
	spark_mesh.radius = 0.022
	spark_mesh.height = 0.044
	spark_mesh.radial_segments = 6
	spark_mesh.rings = 4

	var spark_mat := StandardMaterial3D.new()
	spark_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	spark_mat.vertex_color_use_as_albedo = true
	spark_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	spark_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	spark_mesh.material = spark_mat

	mm.mesh = spark_mesh

	# Hide all pulses offscreen initially
	var hidden_xform := Transform3D(Basis().scaled(Vector3.ZERO), Vector3(0, -999, 0))
	for i in range(max_active_pulses):
		mm.set_instance_transform(i, hidden_xform)
		mm.set_instance_color(i, Color(1, 1, 1, 0))

	_pulses_multimesh.multimesh = mm
	_root_transform_node.add_child(_pulses_multimesh)

func _process(delta: float) -> void:
	_idle_time += delta
	if auto_rotate and not _is_dragging:
		# Gentle idle sinusoidal breathing and subtle yaw
		_yaw += delta * rotation_speed
		_update_camera_transform()

	_update_pulses(delta)

## Updates the connectome neural firing rates and bioluminescent colors
func update_activations(
	cann: DualRingAttractor,
	speed_frac: float = 0.35,
	odor_bearing: float = 0.0,
	odor_strength: float = 0.0,
	sun_bearing: float = 0.0,
	sun_active: bool = false,
	delta: float = 0.016
) -> void:
	if not _nodes_multimesh or not cann:
		return

	var mm: MultiMesh = _nodes_multimesh.multimesh
	if not mm:
		return

	# Gather CANN metrics
	var max_epg: float = 0.01
	for rate in cann.r_epg:
		if rate > max_epg:
			max_epg = rate

	var max_pen_l: float = 0.01
	for rate in cann.r_pen_l:
		if rate > max_pen_l:
			max_pen_l = rate

	var max_pen_r: float = 0.01
	for rate in cann.r_pen_r:
		if rate > max_pen_r:
			max_pen_r = rate

	var shifter_acts: Vector2 = cann.get_shifter_activities()
	var act_l: float = shifter_acts.x
	var act_r: float = shifter_acts.y

	var n_nodes: int = _node_data.size()
	for i in range(n_nodes):
		var node: Dictionary = _node_data[i]
		var reg: String = node.get("region", "")
		var base: float = node.get("base_rate", 18.0)
		var target_hz: float = base

		if reg == "EB":
			var w: int = node.get("wedge", 0)
			var r_epg_w: float = cann.r_epg[w] if w < cann.r_epg.size() else 0.0
			var norm: float = clamp(r_epg_w / max_epg, 0.0, 1.0)
			target_hz = base + pow(norm, 2.2) * 200.0

		elif reg == "PB_L":
			var col: int = node.get("col", 0)
			var r_l: float = cann.r_pen_l[col] if col < cann.r_pen_l.size() else 0.0
			var norm: float = clamp(r_l / max_pen_l, 0.0, 1.0)
			target_hz = base + pow(norm, 1.8) * 190.0

		elif reg == "PB_R":
			var col: int = node.get("col", 0)
			var r_r: float = cann.r_pen_r[col] if col < cann.r_pen_r.size() else 0.0
			var norm: float = clamp(r_r / max_pen_r, 0.0, 1.0)
			target_hz = base + pow(norm, 1.8) * 190.0

		elif reg == "FB":
			var col_i: int = node.get("column", 4)
			var col_phi: float = -PI + (float(col_i) + 0.5) * (TAU / 9.0)
			var d_phi: float = DualRingAttractor.ang_dist(col_phi, odor_bearing)
			var cos_d: float = max(0.0, cos(d_phi))
			target_hz = base + (cos_d * cos_d) * odor_strength * 185.0

		elif reg == "AL_L":
			var side_bias: float = 1.0 + 0.35 * max(0.0, -sin(odor_bearing))
			target_hz = base + pow(odor_strength, 1.2) * side_bias * 175.0

		elif reg == "AL_R":
			var side_bias: float = 1.0 + 0.35 * max(0.0, sin(odor_bearing))
			target_hz = base + pow(odor_strength, 1.2) * side_bias * 175.0

		elif reg == "LAL_L":
			target_hz = base + clamp(act_r * 22.0, 0.0, 180.0)

		elif reg == "LAL_R":
			target_hz = base + clamp(act_l * 22.0, 0.0, 180.0)

		elif reg == "PFL3_L":
			var pfl3_idx: int = node.get("pfl3_idx", 0)
			var rate_pfl3: float = cann.r_pfl3[pfl3_idx] if pfl3_idx < cann.r_pfl3.size() else 0.0
			target_hz = base + pow(clamp(rate_pfl3 / 22.0, 0.0, 1.0), 1.4) * 195.0

		elif reg == "PFL3_R":
			var pfl3_idx: int = node.get("pfl3_idx", 12)
			var rate_pfl3: float = cann.r_pfl3[pfl3_idx] if pfl3_idx < cann.r_pfl3.size() else 0.0
			target_hz = base + pow(clamp(rate_pfl3 / 22.0, 0.0, 1.0), 1.4) * 195.0

		elif reg == "OPTIC_L":
			target_hz = base
			if sun_active and sun_bearing < 0.25:
				target_hz += max(0.0, cos(sun_bearing)) * 145.0

		elif reg == "OPTIC_R":
			target_hz = base
			if sun_active and sun_bearing > -0.25:
				target_hz += max(0.0, cos(sun_bearing)) * 145.0

		elif reg.begins_with("VNC_"):
			var is_cord: bool = node.get("is_cord", false)
			if is_cord:
				var side: String = node.get("side", "L")
				var side_drive: float = act_l if side == "L" else act_r
				target_hz = base + (side_drive / 5.0) * 110.0 + speed_frac * 80.0
			else:
				target_hz = base + speed_frac * 24.0

		else: # PROTOCEREBRUM & SCAFFOLD
			var spont: float = sin(_idle_time * 2.5 + float(i) * 0.08)
			target_hz = base + max(0.0, spont) * 18.0

		# Relax current rate toward target
		var curr_hz: float = _node_rates[i]
		curr_hz += (target_hz - curr_hz) * min(1.0, 14.0 * delta)
		_node_rates[i] = curr_hz

		# High-fidelity Biological Neon Colormap
		var col := _compute_node_color(reg, curr_hz, node)
		mm.set_instance_color(i, col)

func _compute_node_color(reg: String, hz: float, node: Dictionary) -> Color:
	var f: float = clamp((hz - 15.0) / 160.0, 0.0, 1.0)

	if reg == "EB":
		# Ellipsoid Body (E-PG Compass): Deep Teal resting -> Vivid Neon Cyan active bump
		var c_rest := Color(0.06, 0.24, 0.32, 0.38)
		var c_active := Color(0.12, 0.98, 0.88, 0.96)
		return c_rest.lerp(c_active, f)

	elif reg == "PB_L" or reg == "PB_R":
		# Protocerebral Bridge (P-EN Shifters): Dark Wine resting -> Hot Neon Magenta active
		var c_rest := Color(0.28, 0.08, 0.22, 0.38)
		var c_active := Color(0.98, 0.16, 0.65, 0.96)
		return c_rest.lerp(c_active, f)

	elif reg == "FB":
		# Fan-Shaped Body (9-Col Sensory Grid): Dark Pine resting -> Vivid Emerald active
		var c_rest := Color(0.08, 0.24, 0.14, 0.38)
		var c_active := Color(0.12, 0.96, 0.53, 0.96)
		return c_rest.lerp(c_active, f)

	elif reg == "AL_L" or reg == "AL_R":
		# Antennal Lobes (Olfactory Glomeruli): Dark Moss resting -> Citrus Mint active
		var c_rest := Color(0.10, 0.24, 0.14, 0.38)
		var c_active := Color(0.20, 0.94, 0.43, 0.96)
		return c_rest.lerp(c_active, f)

	elif reg == "PFL3_L" or reg == "LAL_L":
		# Left Steering Pathway: Azure Sky Blue
		var c_rest := Color(0.08, 0.22, 0.45, 0.38)
		var c_active := Color(0.15, 0.72, 1.00, 0.96)
		return c_rest.lerp(c_active, f)

	elif reg == "PFL3_R" or reg == "LAL_R":
		# Right Steering Pathway: Electric Tangerine / Amber
		var c_rest := Color(0.42, 0.18, 0.08, 0.38)
		var c_active := Color(1.00, 0.48, 0.18, 0.96)
		return c_rest.lerp(c_active, f)

	elif reg.begins_with("VNC_"):
		if node.get("is_cord", false):
			var side: String = node.get("side", "L")
			var tint := Color(0.15, 0.72, 1.0) if side == "L" else Color(1.0, 0.48, 0.18)
			return Color(0.15, 0.28, 0.42, 0.4).lerp(tint, f)
		else:
			return Color(0.16, 0.28, 0.40, 0.28).lerp(Color(0.45, 0.75, 0.95, 0.8), f * 0.7)

	else:
		# Scaffold envelope (Optic Lobes, Protocerebrum)
		var c_dim := Color(0.16, 0.22, 0.32, 0.18)
		var c_lit := Color(0.35, 0.55, 0.75, 0.45)
		return c_dim.lerp(c_lit, f * 0.6)

func _update_pulses(delta: float) -> void:
	if not _pulses_multimesh:
		return

	var mm: MultiMesh = _pulses_multimesh.multimesh
	if not mm:
		return

	_pulse_timer += delta

	# Spawn new pulses if active edges are high firing
	if _pulse_timer > 0.045 and _pulses.size() < max_active_pulses and not _actionable_edges.is_empty():
		_pulse_timer = 0.0
		# Try random candidate edges
		for _attempt in range(4):
			var edge: Dictionary = _actionable_edges.pick_random()
			var src_idx: int = edge["src"]
			var rate: float = _node_rates[src_idx] if src_idx < _node_rates.size() else 0.0
			if rate > 32.0:
				var p := SynapticPulse.new()
				p.src_pos = edge["src_pos"]
				p.dst_pos = edge["dst_pos"]
				p.progress = 0.0
				p.speed = randf_range(2.4, 4.2)
				var etype: String = edge["type"]
				if etype.begins_with("PFL3_L"):
					p.color = Color(0.2, 0.85, 1.0, 1.0)
				elif etype.begins_with("PFL3_R"):
					p.color = Color(1.0, 0.55, 0.2, 1.0)
				elif etype == "AL_FB":
					p.color = Color(0.2, 1.0, 0.5, 1.0)
				elif etype == "EPG_PB" or etype == "EB_RING":
					p.color = Color(0.1, 1.0, 0.9, 1.0)
				elif etype.begins_with("VNC"):
					p.color = Color(0.7, 0.9, 1.0, 1.0)
				else:
					p.color = Color(1.0, 0.85, 0.4, 1.0)
				p.size = randf_range(0.8, 1.4)
				_pulses.append(p)
				break

	# Advance pulses
	var living_pulses: Array[SynapticPulse] = []
	for p in _pulses:
		p.progress += p.speed * delta
		if p.progress < 1.0:
			living_pulses.append(p)
	_pulses = living_pulses

	# Update MultiMesh transforms & colors
	var hidden_xform := Transform3D(Basis().scaled(Vector3.ZERO), Vector3(0, -999, 0))
	for i in range(max_active_pulses):
		if i < _pulses.size():
			var p = _pulses[i]
			var cur_pos: Vector3 = p.src_pos.lerp(p.dst_pos, p.progress)
			# Pulsing glow intensity: peaks in middle
			var alpha_factor: float = sin(p.progress * PI)
			var xform := Transform3D(Basis().scaled(Vector3.ONE * (p.size * (0.8 + 0.4 * alpha_factor))), cur_pos)
			mm.set_instance_transform(i, xform)
			var col: Color = p.color
			col.a = alpha_factor
			mm.set_instance_color(i, col)
		else:
			mm.set_instance_transform(i, hidden_xform)
			mm.set_instance_color(i, Color(1, 1, 1, 0))

## Interactive Orbit / Drag & Zoom Controls
func handle_gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT or event.button_index == MOUSE_BUTTON_RIGHT:
			if event.pressed:
				_is_dragging = true
				_last_mouse_pos = event.position
			else:
				_is_dragging = false
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			_zoom_distance = clamp(_zoom_distance - 0.18, 1.1, 4.8)
			_update_camera_transform()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			_zoom_distance = clamp(_zoom_distance + 0.18, 1.1, 4.8)
			_update_camera_transform()

	elif event is InputEventMouseMotion and _is_dragging:
		var delta_pos: Vector2 = event.position - _last_mouse_pos
		_last_mouse_pos = event.position
		_yaw -= delta_pos.x * 0.008
		_pitch = clamp(_pitch - delta_pos.y * 0.008, -1.2, 1.2)
		_update_camera_transform()

func reset_camera_view() -> void:
	_yaw = 0.0
	_pitch = 0.22
	_zoom_distance = 2.85
	_update_camera_transform()

func _update_camera_transform() -> void:
	if _cam_pivot and _cam_pitch_node and camera:
		_cam_pivot.rotation.y = _yaw
		_cam_pitch_node.rotation.x = _pitch
		camera.position = Vector3(0, 0, _zoom_distance)
		camera.look_at(_cam_pivot.global_position, Vector3.UP)
		camera_moved.emit(rad_to_deg(_yaw), rad_to_deg(_pitch), _zoom_distance)
