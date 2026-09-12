class_name DualRingAttractor
extends RefCounted

## Continuous Attractor Neural Network (CANN) Engine
## Simulates the Drosophila Central Complex Heading Compass:
##   - 48 E-PG compass neurons on Ellipsoid Body (EB) azimuth [0, 2pi)
##   - 24 P-EN_L left shifter neurons (-45 deg shift)
##   - 24 P-EN_R right shifter neurons (+45 deg shift)
##   - 2.09x biological feedback-to-feedforward torque ratio
##   - Divisive normalization in EB
##   - 24 PFL3 comparator neurons for biological push-pull chemotaxis & phototaxis

const N_EPG: int = 48
const N_PEN_SIDE: int = 24
const N_PEN_TOTAL: int = 48
const N_PFL3_SIDE: int = 12
const N_PFL3_TOTAL: int = 24
const N_FB_COLS: int = 24

# Biophysical Constants
const TAU_M: float = 0.020 # 20 ms membrane time constant
const TAU_PFL3: float = 0.025 # 25 ms PFL3 time constant
const K_DIV: float = 0.012 # Divisive normalization factor
const W_EE_BASE: float = 1.0
const W_EP_BASE: float = 0.8
const W_PE_RATIO: float = 2.09 # Connectome biological ratio
const SHIFT_ANGLE: float = PI / 4.0 # 45 degrees
const SIGMA_EE: float = 0.5236 # 30 degrees (pi/6)
const K_TURN_DRIVE: float = 2.5
const G_VISUAL_GAIN: float = 2.0
const NOISE_SIGMA: float = 0.015
const SUBSTEPS_PER_FRAME: int = 8

# Preferred Azimuthal Angles
var theta_epg: PackedFloat32Array
var theta_pen_l: PackedFloat32Array
var theta_pen_r: PackedFloat32Array
var fb_angles: PackedFloat32Array

# Firing Rates (Hz normalized)
var r_epg: PackedFloat32Array
var r_pen_l: PackedFloat32Array
var r_pen_r: PackedFloat32Array
var r_pfl3: PackedFloat32Array

# 4-Block Synaptic Matrices (flattened row-major)
var W_ee: PackedFloat32Array       # 48 x 48
var W_ep_l: PackedFloat32Array     # 24 x 48
var W_ep_r: PackedFloat32Array     # 24 x 48
var W_pe_l: PackedFloat32Array     # 48 x 24
var W_pe_r: PackedFloat32Array     # 48 x 24
var W_ep_pfl3: PackedFloat32Array  # 24 x 48
var W_fb_pfl3: PackedFloat32Array  # 24 x 24

func _init() -> void:
	_init_arrays()
	_build_synaptic_matrices()
	reset(0.0)

static func wrap_angle(angle: float) -> float:
	return fposmod(angle + PI, TAU) - PI

static func ang_dist(a1: float, a2: float) -> float:
	return wrap_angle(a1 - a2)

func _init_arrays() -> void:
	theta_epg.resize(N_EPG)
	for i in range(N_EPG):
		theta_epg[i] = float(i) * TAU / float(N_EPG)
		
	theta_pen_l.resize(N_PEN_SIDE)
	theta_pen_r.resize(N_PEN_SIDE)
	for i in range(N_PEN_SIDE):
		theta_pen_l[i] = float(i) * TAU / float(N_PEN_SIDE)
		theta_pen_r[i] = float(i) * TAU / float(N_PEN_SIDE)
		
	fb_angles.resize(N_FB_COLS)
	for i in range(N_FB_COLS):
		fb_angles[i] = -PI + float(i) * TAU / float(N_FB_COLS)
		
	r_epg.resize(N_EPG)
	r_pen_l.resize(N_PEN_SIDE)
	r_pen_r.resize(N_PEN_SIDE)
	r_pfl3.resize(N_PFL3_TOTAL)

func _build_synaptic_matrices() -> void:
	var two_sigma_sq: float = 2.0 * (SIGMA_EE * SIGMA_EE)
	var w_pe_strength: float = W_EP_BASE * W_PE_RATIO
	
	# 1. W_ee: Local Gaussian recurrent excitation in E-PG (48 x 48)
	W_ee.resize(N_EPG * N_EPG)
	for i in range(N_EPG):
		for j in range(N_EPG):
			var d: float = ang_dist(theta_epg[i], theta_epg[j])
			W_ee[i * N_EPG + j] = W_EE_BASE * exp(-(d * d) / two_sigma_sq)
			
	# 2. W_ep: E-PG -> P-EN forward projection (24 x 48)
	W_ep_l.resize(N_PEN_SIDE * N_EPG)
	W_ep_r.resize(N_PEN_SIDE * N_EPG)
	for i in range(N_PEN_SIDE):
		for j in range(N_EPG):
			var d_l: float = ang_dist(theta_pen_l[i], theta_epg[j])
			W_ep_l[i * N_EPG + j] = W_EP_BASE * exp(-(d_l * d_l) / two_sigma_sq)
			var d_r: float = ang_dist(theta_pen_r[i], theta_epg[j])
			W_ep_r[i * N_EPG + j] = W_EP_BASE * exp(-(d_r * d_r) / two_sigma_sq)
			
	# 3. W_pe: P-EN -> E-PG phase-shifted feedback (48 x 24)
	W_pe_l.resize(N_EPG * N_PEN_SIDE)
	W_pe_r.resize(N_EPG * N_PEN_SIDE)
	for i in range(N_EPG):
		for j in range(N_PEN_SIDE):
			var target_l: float = wrap_angle(theta_pen_l[j] - SHIFT_ANGLE)
			var d_pe_l: float = ang_dist(theta_epg[i], target_l)
			W_pe_l[i * N_PEN_SIDE + j] = w_pe_strength * exp(-(d_pe_l * d_pe_l) / two_sigma_sq)
			
			var target_r: float = wrap_angle(theta_pen_r[j] + SHIFT_ANGLE)
			var d_pe_r: float = ang_dist(theta_epg[i], target_r)
			W_pe_r[i * N_PEN_SIDE + j] = w_pe_strength * exp(-(d_pe_r * d_pe_r) / two_sigma_sq)
			
	# 4. PFL3 Comparator Synaptic Weights
	W_ep_pfl3.resize(N_PFL3_TOTAL * N_EPG)
	for i in range(N_PFL3_SIDE):
		var th_l: float = (float(i) + 0.5) * (TAU / float(N_PFL3_SIDE))
		for j in range(N_EPG):
			var d_l: float = ang_dist(theta_epg[j], th_l)
			W_ep_pfl3[i * N_EPG + j] = exp(-(d_l * d_l) / (2.0 * 0.25)) * 15.0
			
		var th_r: float = (float(i) + 0.5) * (TAU / float(N_PFL3_SIDE))
		for j in range(N_EPG):
			var d_r: float = ang_dist(theta_epg[j], th_r)
			W_ep_pfl3[(N_PFL3_SIDE + i) * N_EPG + j] = exp(-(d_r * d_r) / (2.0 * 0.25)) * 15.0
			
	W_fb_pfl3.resize(N_PFL3_TOTAL * N_FB_COLS)
	for i in range(N_PFL3_SIDE):
		for j in range(N_FB_COLS):
			# Left PFL3 prefers -90 deg (-PI/2)
			var d_fb_l: float = ang_dist(fb_angles[j], -PI * 0.5)
			var cos_l: float = max(0.0, cos(d_fb_l))
			W_fb_pfl3[i * N_FB_COLS + j] = (cos_l * cos_l) * 2.5
			# Right PFL3 prefers +90 deg (+PI/2)
			var d_fb_r: float = ang_dist(fb_angles[j], PI * 0.5)
			var cos_r: float = max(0.0, cos(d_fb_r))
			W_fb_pfl3[(N_PFL3_SIDE + i) * N_FB_COLS + j] = (cos_r * cos_r) * 2.5

func reset(initial_heading: float = 0.0) -> void:
	for i in range(N_EPG):
		var d: float = ang_dist(theta_epg[i], initial_heading)
		r_epg[i] = max(0.0, cos(d)) * 2.0
	for i in range(N_PEN_SIDE):
		r_pen_l[i] = 0.0
		r_pen_r[i] = 0.0
	for i in range(N_PFL3_TOTAL):
		r_pfl3[i] = 0.0

func step(dt: float, omega: float = 0.0, cue_angle: float = 0.0, cue_active: bool = false) -> void:
	var h_data: Dictionary = decode_heading()
	var h_current: float = h_data["heading"]
	
	var g_l: float = K_TURN_DRIVE * max(0.0, -omega)
	var g_r: float = K_TURN_DRIVE * max(0.0, omega)
	
	# Visual Landmark / Sun Anchor
	var u_vis_e := PackedFloat32Array()
	u_vis_e.resize(N_EPG)
	if cue_active:
		var err_cue: float = ang_dist(cue_angle, h_current)
		var omega_cue: float = 3.5 * clamp(err_cue, -3.0, 3.0)
		g_l += max(0.0, -omega_cue)
		g_r += max(0.0, omega_cue)
		for i in range(N_EPG):
			var d_vis: float = ang_dist(theta_epg[i], cue_angle)
			var cos_vis: float = max(0.0, cos(d_vis))
			u_vis_e[i] = G_VISUAL_GAIN * (cos_vis * cos_vis)
	else:
		u_vis_e.fill(0.0)
		
	# 1. Update P-EN Shifter Dynamics
	for i in range(N_PEN_SIDE):
		var sum_l: float = 0.0
		var sum_r: float = 0.0
		var row_offset: int = i * N_EPG
		for j in range(N_EPG):
			var ep_rate: float = r_epg[j]
			sum_l += W_ep_l[row_offset + j] * ep_rate
			sum_r += W_ep_r[row_offset + j] * ep_rate
			
		var u_pen_l: float = sum_l * (0.05 + 0.25 * g_l)
		var u_pen_r: float = sum_r * (0.05 + 0.25 * g_r)
		
		var dr_pen_l: float = (-r_pen_l[i] + u_pen_l) / TAU_M
		var dr_pen_r: float = (-r_pen_r[i] + u_pen_r) / TAU_M
		
		r_pen_l[i] = max(0.0, r_pen_l[i] + dt * dr_pen_l)
		r_pen_r[i] = max(0.0, r_pen_r[i] + dt * dr_pen_r)
		
	# 2. Update E-PG Compass with Recurrent + Phase-Shift Feedback + Divisive Norm
	var u_e := PackedFloat32Array()
	u_e.resize(N_EPG)
	var sum_sq: float = 0.0
	
	for i in range(N_EPG):
		var sum_recurrent: float = 0.0
		var row_offset_ee: int = i * N_EPG
		for j in range(N_EPG):
			sum_recurrent += W_ee[row_offset_ee + j] * r_epg[j]
			
		var sum_pe_l: float = 0.0
		var sum_pe_r: float = 0.0
		var row_offset_pe: int = i * N_PEN_SIDE
		for j in range(N_PEN_SIDE):
			sum_pe_l += W_pe_l[row_offset_pe + j] * r_pen_l[j]
			sum_pe_r += W_pe_r[row_offset_pe + j] * r_pen_r[j]
			
		var val_e: float = sum_recurrent + 0.30 * (sum_pe_l + sum_pe_r) + u_vis_e[i]
		if NOISE_SIGMA > 0.0:
			val_e += randfn(0.0, NOISE_SIGMA)
		var pos_val: float = max(0.0, val_e)
		u_e[i] = pos_val
		sum_sq += pos_val * pos_val
		
	# Divisive Normalization
	var norm_denom: float = 1.0 + K_DIV * sum_sq
	for i in range(N_EPG):
		var phi_e: float = (u_e[i] * u_e[i]) / norm_denom
		var dr_epg: float = (-r_epg[i] + phi_e) / TAU_M
		r_epg[i] = max(0.0, r_epg[i] + dt * dr_epg)

func step_frame(dt_frame: float, omega: float = 0.0, cue_angle: float = 0.0, cue_active: bool = false) -> void:
	var dt_sub: float = dt_frame / float(SUBSTEPS_PER_FRAME)
	for k in range(SUBSTEPS_PER_FRAME):
		step(dt_sub, omega, cue_angle, cue_active)

func decode_heading() -> Dictionary:
	var x: float = 0.0
	var y: float = 0.0
	var total_rate: float = 0.0
	for i in range(N_EPG):
		var rate: float = r_epg[i]
		var angle: float = theta_epg[i]
		x += rate * cos(angle)
		y += rate * sin(angle)
		total_rate += rate
	var amplitude: float = sqrt(x * x + y * y)
	var coherence: float = min(1.0, amplitude / (total_rate + 1e-6))
	var heading: float = atan2(y, x)
	return {
		"heading": heading,
		"amplitude": amplitude,
		"coherence": coherence
	}

func get_shifter_activities() -> Vector2:
	var sum_l: float = 0.0
	var sum_r: float = 0.0
	for i in range(N_PEN_SIDE):
		sum_l += r_pen_l[i]
		sum_r += r_pen_r[i]
	return Vector2(sum_l / float(N_PEN_SIDE), sum_r / float(N_PEN_SIDE))

func step_pfl3(relative_bearing: float, odor_strength: float, dt: float) -> Dictionary:
	# Odor array in Fan-Shaped Body (FB) 24 columns
	var u_odor := PackedFloat32Array()
	u_odor.resize(N_FB_COLS)
	for j in range(N_FB_COLS):
		var d: float = ang_dist(fb_angles[j], relative_bearing)
		var cos_d: float = max(0.0, cos(d))
		u_odor[j] = odor_strength * (cos_d * cos_d)
		
	# Coincidence drive: E-PG + FB -> PFL3
	for i in range(N_PFL3_TOTAL):
		var epg_drive: float = 0.0
		var row_epg: int = i * N_EPG
		for j in range(N_EPG):
			epg_drive += W_ep_pfl3[row_epg + j] * r_epg[j]
		epg_drive *= 0.01
		
		var fb_drive: float = 0.0
		var row_fb: int = i * N_FB_COLS
		for j in range(N_FB_COLS):
			fb_drive += W_fb_pfl3[row_fb + j] * u_odor[j]
		fb_drive *= 0.8
		
		var phi: float = max(0.0, epg_drive + fb_drive)
		var dr_pfl3: float = (-r_pfl3[i] + phi) / TAU_PFL3
		r_pfl3[i] = max(0.0, r_pfl3[i] + dt * dr_pfl3)
		
	var sum_l: float = 0.0
	var sum_r: float = 0.0
	for i in range(N_PFL3_SIDE):
		sum_l += r_pfl3[i]
		sum_r += r_pfl3[N_PFL3_SIDE + i]
		
	var diff: float = (sum_r - sum_l) / float(N_PFL3_TOTAL)
	var k_drive: float = 2.8
	var omega_auto: float = clamp((k_drive * diff) / 4.5, -k_drive, k_drive)
	
	var tot: float = sum_l + sum_r
	var bias: float = (sum_r - sum_l) / tot if tot > 1e-4 else 0.0
	
	return {
		"omega_auto": omega_auto,
		"mean_l": sum_l / float(N_PFL3_SIDE),
		"mean_r": sum_r / float(N_PFL3_SIDE),
		"bias": clamp(bias, -1.0, 1.0)
	}

func get_active_synaptic_arcs(threshold_ratio: float = 0.35) -> Array:
	var arcs := []
	var max_l: float = 0.0
	var max_r: float = 0.0
	for i in range(N_PEN_SIDE):
		if r_pen_l[i] > max_l: max_l = r_pen_l[i]
		if r_pen_r[i] > max_r: max_r = r_pen_r[i]
		
	if max_l > 0.5:
		var thresh_l: float = max_l * threshold_ratio
		for i in range(N_PEN_SIDE):
			if r_pen_l[i] > thresh_l:
				# Find peak EPG target
				var best_target: int = 0
				var best_weight: float = -1.0
				for j in range(N_EPG):
					var w: float = W_pe_l[j * N_PEN_SIDE + i]
					if w > best_weight:
						best_weight = w
						best_target = j
				arcs.append({
					"type": "LEFT",
					"pen_idx": i,
					"pen_angle": theta_pen_l[i],
					"epg_idx": best_target,
					"epg_angle": theta_epg[best_target],
					"intensity": min(1.0, r_pen_l[i] / (max_l + 1e-6))
				})
				
	if max_r > 0.5:
		var thresh_r: float = max_r * threshold_ratio
		for i in range(N_PEN_SIDE):
			if r_pen_r[i] > thresh_r:
				var best_target: int = 0
				var best_weight: float = -1.0
				for j in range(N_EPG):
					var w: float = W_pe_r[j * N_PEN_SIDE + i]
					if w > best_weight:
						best_weight = w
						best_target = j
				arcs.append({
					"type": "RIGHT",
					"pen_idx": i,
					"pen_angle": theta_pen_r[i],
					"epg_idx": best_target,
					"epg_angle": theta_epg[best_target],
					"intensity": min(1.0, r_pen_r[i] / (max_r + 1e-6))
				})
	return arcs
