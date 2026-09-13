class_name PaintingCanvas3D
extends MeshInstance3D

## PaintingCanvas3D: Dynamic Real-Time Canvas Mesh for Godot 4.7+
## Receives telemetry from Python Fruitfly V2 simulation via UDP (port 8999),
## updates 3D dynamic texture in real-time, and mirrors fly agent kinematics.

@export var udp_port: int = 8999
@export var canvas_size: int = 256
@export var fly_agent_node: Node3D = null

var udp: PacketPeerUDP = null
var canvas_image: Image = null
var canvas_texture: ImageTexture = null
var material: StandardMaterial3D = null
var dirty_canvas: bool = false

# Canvas 3D bounds in tabletop coordinates
var canvas_x_min: float = -1.28
var canvas_x_max: float = 1.28
var canvas_z_min: float = -1.28
var canvas_z_max: float = 1.28

func _ready() -> void:
	print("[PaintingCanvas3D] Initializing dynamic 256x256 canvas surface...")
	udp = PacketPeerUDP.new()
	var err = udp.bind(udp_port)
	if err == OK:
		print("[PaintingCanvas3D] Listening for Python telemetry on UDP port ", udp_port)
	else:
		print("[PaintingCanvas3D] Failed to bind UDP port ", udp_port)

	# Initialize pristine white image buffer
	canvas_image = Image.create(canvas_size, canvas_size, false, Image.FORMAT_RGB8)
	canvas_image.fill(Color(1.0, 1.0, 1.0))
	canvas_texture = ImageTexture.create_from_image(canvas_image)

	# Setup PBR Material with Dynamic Canvas Texture
	material = StandardMaterial3D.new()
	material.albedo_texture = canvas_texture
	material.roughness = 0.8
	material_override = material

func _process(_delta: float) -> void:
	if udp == null or not udp.is_bound():
		return

	dirty_canvas = false

	while udp.get_available_packet_count() > 0:
		var raw_packet: PackedByteArray = udp.get_packet()
		var text: String = raw_packet.get_string_from_utf8()
		var json_result = JSON.parse_string(text)

		if typeof(json_result) == TYPE_DICTIONARY:
			_handle_telemetry_packet(json_result)

	if dirty_canvas:
		canvas_texture.update(canvas_image)

func _handle_telemetry_packet(data: Dictionary) -> void:
	if not data.has("fly_pos"):
		return

	var f_pos = data["fly_pos"] # [x, y, z]
	var fly_3d_pos = Vector3(float(f_pos[0]), float(f_pos[1]), float(f_pos[2]))
	var heading: float = float(data.get("fly_theta", 0.0))

	# Update 3D Fly Agent representation if connected
	if is_instance_valid(fly_agent_node):
		fly_agent_node.global_position = fly_3d_pos
		fly_agent_node.rotation.y = -heading

	# Check brush contact on dynamic canvas
	var in_contact: bool = bool(data.get("brush_in_contact", false))
	if in_contact:
		var pressure: float = float(data.get("brush_pressure", 1.0))
		var col_arr = data.get("brush_color", [1.0, 0.0, 0.0])
		var color = Color(float(col_arr[0]), float(col_arr[1]), float(col_arr[2]))
		_deposit_pigment(fly_3d_pos.x, fly_3d_pos.z, color, pressure)

func _deposit_pigment(world_x: float, world_z: float, color: Color, pressure: float) -> void:
	if world_x < canvas_x_min or world_x > canvas_x_max or world_z < canvas_z_min or world_z > canvas_z_max:
		return

	# Map world [-1.28, 1.28] to pixel coordinates [0, 255]
	var u: int = int(((world_x - canvas_x_min) / (canvas_x_max - canvas_x_min)) * float(canvas_size))
	var v: int = int(((world_z - canvas_z_min) / (canvas_z_max - canvas_z_min)) * float(canvas_size))

	var stamp_radius: int = max(2, int(4.0 * pressure))

	for dy in range(-stamp_radius, stamp_radius + 1):
		for dx in range(-stamp_radius, stamp_radius + 1):
			if dx * dx + dy * dy <= stamp_radius * stamp_radius:
				var px: int = clampi(u + dx, 0, canvas_size - 1)
				var py: int = clampi(v + dy, 0, canvas_size - 1)
				var existing: Color = canvas_image.get_pixel(px, py)
				var blended: Color = existing.lerp(color, clampf(0.3 * pressure, 0.0, 1.0))
				canvas_image.set_pixel(px, py, blended)
				dirty_canvas = true
