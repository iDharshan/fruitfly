class_name CompassWidget
extends Control

## Avionics 360-degree Bio-Compass Rose & Odor Target Radar
## Renders vector circular compass dial with cardinal markers,
## retinotopic celestial sun beacon angle, and egocentric odor bearing needle (Psi).

@export var heading_deg: float = 0.0
@export var odor_bearing_rad: float = 0.0
@export var odor_strength: float = 0.0
@export var sun_azimuth_rad: float = 0.0
@export var sun_active: bool = false

var _cached_font: Font

func _ready() -> void:
	_cached_font = ThemeDB.fallback_font

func update_telemetry(
	p_heading_deg: float,
	p_odor_bearing: float,
	p_odor_str: float,
	p_sun_azimuth: float,
	p_sun_active: bool
) -> void:
	heading_deg = p_heading_deg
	odor_bearing_rad = p_odor_bearing
	odor_strength = p_odor_str
	sun_azimuth_rad = p_sun_azimuth
	sun_active = p_sun_active
	queue_redraw()

func _draw() -> void:
	var center := size * 0.5
	var radius: float = min(center.x, center.y) - 6.0
	if radius <= 10.0:
		return

	# 1. Dark Glass Dial Background
	draw_circle(center, radius, Color(0.02, 0.06, 0.10, 0.78))
	draw_arc(center, radius, 0.0, TAU, 48, Color(0.15, 0.72, 0.95, 0.65), 1.8)
	draw_arc(center, radius * 0.68, 0.0, TAU, 32, Color(0.12, 0.45, 0.65, 0.35), 1.0)

	# 2. Rotating Cardinal Tick Marks & Labels
	var heading_rad: float = deg_to_rad(heading_deg)
	var cardinals := [
		{"angle": 0.0, "label": "N", "col": Color(1.0, 0.32, 0.28, 1.0)},
		{"angle": PI * 0.25, "label": "NE", "col": Color(0.55, 0.75, 0.85, 0.7)},
		{"angle": PI * 0.5, "label": "E", "col": Color(0.20, 0.85, 1.0, 0.9)},
		{"angle": PI * 0.75, "label": "SE", "col": Color(0.55, 0.75, 0.85, 0.7)},
		{"angle": PI, "label": "S", "col": Color(0.20, 0.85, 1.0, 0.9)},
		{"angle": PI * 1.25, "label": "SW", "col": Color(0.55, 0.75, 0.85, 0.7)},
		{"angle": PI * 1.5, "label": "W", "col": Color(0.20, 0.85, 1.0, 0.9)},
		{"angle": PI * 1.75, "label": "NW", "col": Color(0.55, 0.75, 0.85, 0.7)}
	]

	for c in cardinals:
		# Angle relative to current fly nose (which points straight up at -PI/2)
		var rel_ang: float = (c["angle"] - heading_rad) - (PI * 0.5)
		var p_outer := center + Vector2(cos(rel_ang), sin(rel_ang)) * (radius - 2.0)
		var p_inner := center + Vector2(cos(rel_ang), sin(rel_ang)) * (radius - 8.0)
		draw_line(p_inner, p_outer, c["col"], 1.5)

		var p_text := center + Vector2(cos(rel_ang), sin(rel_ang)) * (radius - 18.0)
		if _cached_font:
			var txt: String = c["label"]
			var f_size: int = 11 if txt.length() == 1 else 9
			draw_string(
				_cached_font,
				p_text + Vector2(-6, 4),
				txt,
				HORIZONTAL_ALIGNMENT_CENTER,
				-1,
				f_size,
				c["col"]
			)

	# 3. Sun Beacon Retinotopic Marker (Gold)
	if sun_active:
		var sun_rel: float = (sun_azimuth_rad - heading_rad) - (PI * 0.5)
		var sun_pos := center + Vector2(cos(sun_rel), sin(sun_rel)) * (radius - 3.0)
		draw_circle(sun_pos, 4.5, Color(1.0, 0.85, 0.22, 0.95))
		draw_arc(sun_pos, 7.0, 0.0, TAU, 16, Color(1.0, 0.92, 0.45, 0.75), 1.2)

	# 4. Odor Target Relative Bearing Needle (Emerald / Lime)
	if odor_strength > 0.02:
		# odor_bearing_rad is already relative to fly nose
		var odor_ang: float = odor_bearing_rad - (PI * 0.5)
		var odor_pos := center + Vector2(cos(odor_ang), sin(odor_ang)) * (radius * 0.85)
		var arrow_col := Color(0.18, 0.98, 0.55, 0.85)
		draw_line(center, odor_pos, arrow_col, 2.0)
		draw_circle(odor_pos, 3.5, arrow_col)

	# 5. Central Fly Vessel Indicator
	var nose := center + Vector2(0, -radius * 0.38)
	var wing_l := center + Vector2(-radius * 0.24, radius * 0.20)
	var wing_r := center + Vector2(radius * 0.24, radius * 0.20)
	var tail := center + Vector2(0, radius * 0.12)
	var fly_pts := PackedVector2Array([nose, wing_r, tail, wing_l])
	draw_colored_polygon(fly_pts, Color(0.15, 0.95, 0.85, 0.85))
	draw_polyline(PackedVector2Array([nose, wing_r, tail, wing_l, nose]), Color(1, 1, 1, 0.9), 1.4)
