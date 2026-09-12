extends SceneTree

## Headless test script to validate DualRingAttractor CANN dynamics in Godot 4.7.2

func _init() -> void:
	print("--- Running CANN Dual Ring Attractor Validation ---")
	var attractor = DualRingAttractor.new()
	
	# Test 1: Initial Bump Coherence (analytical half-wave cosine seed is pi/4 = 78.5%)
	attractor.reset(0.0)
	var h0 = attractor.decode_heading()
	print("Initial Decoded Heading: ", snapped(rad_to_deg(h0["heading"]), 0.1), " deg")
	print("Initial Coherence: ", snapped(h0["coherence"] * 100.0, 0.1), " %")
	assert(abs(h0["heading"]) < 0.1, "Initial heading must be near 0")
	assert(h0["coherence"] > 0.75, "Initial unrelaxed coherence must be > 75%")
	
	# Relax for 10 frames to let divisive normalization sharpen the bump
	for k in range(10):
		attractor.step_frame(1.0 / 60.0, 0.0, 0.0, false)
	var h_relaxed = attractor.decode_heading()
	print("Relaxed Coherence after normalization: ", snapped(h_relaxed["coherence"] * 100.0, 0.1), " %")
	assert(h_relaxed["coherence"] > 0.80, "Relaxed bump coherence must be > 80%")
	
	# Test 2: Integrate 60 frames with Right Turn Angular Velocity (omega = +2.0)
	print("\nTesting Right Turn Angular Velocity (omega = +2.0)...")
	for frame in range(60):
		attractor.step_frame(1.0 / 60.0, 2.0, 0.0, false)
		
	var h1 = attractor.decode_heading()
	var pen_act = attractor.get_shifter_activities()
	print("Decoded Heading after Right Turn: ", snapped(rad_to_deg(h1["heading"]), 0.1), " deg")
	print("Coherence: ", snapped(h1["coherence"] * 100.0, 0.1), " %")
	print("Shifter Activities (L, R): (", snapped(pen_act.x, 0.01), ", ", snapped(pen_act.y, 0.01), ")")
	assert(pen_act.y > pen_act.x, "Right P-EN shifter must be more active during right turn")
	assert(h1["coherence"] > 0.60, "Attractor must remain stable during turns")
	
	# Test 3: Biological PFL3 Comparator
	print("\nTesting Biological PFL3 Push-Pull Steering...")
	var pfl3_res_left = attractor.step_pfl3(-PI * 0.5, 0.8, 0.016)
	print("Odor Left (-90 deg) -> Omega: ", snapped(pfl3_res_left["omega_auto"], 0.01), ", Bias: ", snapped(pfl3_res_left["bias"], 0.01))
	assert(pfl3_res_left["omega_auto"] > 0, "Odor on left must yield leftward steering (+Y rotation)")
	
	var pfl3_res_right = attractor.step_pfl3(PI * 0.5, 0.8, 0.016)
	print("Odor Right (+90 deg) -> Omega: ", snapped(pfl3_res_right["omega_auto"], 0.01), ", Bias: ", snapped(pfl3_res_right["bias"], 0.01))
	assert(pfl3_res_right["omega_auto"] < 0, "Odor on right must yield rightward steering (-Y rotation)")
	
	print("\n===> ALL CANN CIRCUIT TESTS PASSED SUCCESSFULLY! <===")
	quit(0)
