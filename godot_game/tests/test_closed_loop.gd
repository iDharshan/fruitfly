extends SceneTree

## Headless Closed-Loop Neuro-Flight & Autonomous Navigation Test Suite
## Validates:
##  1. 3D Volumetric Odor Field bilateral antenna sampling & ambient wind advection
##  2. Autonomous In-Plume SURGE Anemotaxis & PFL3 gradient ascending
##  3. Autonomous Lost-Plume CAST Anemotaxis (Currea et al. 2026 alternating crosswind sweeps)
##  4. Celestial Sun Beacon retinotopic guidance ray & allocentric azimuth anchoring
##  5. Food consumption event & metabolic energy replenishment

func _init() -> void:
	process_frame.connect(_run_test, CONNECT_ONE_SHOT)

func _run_test() -> void:
	print("--- Running Closed-Loop Neuro-Flight & Auto-Navigation Tests ---")
	
	var arena_scene: PackedScene = load("res://scenes/main_arena.tscn")
	var arena: MainArena = arena_scene.instantiate() as MainArena
	root.add_child(arena)
	
	# Wait for physics frames for arena and children to call _ready() and settle
	for k in range(3):
		await physics_frame
	
	var fly: FlyAgent = arena.fly_agent
	var odor_field: VolumetricOdorField = arena.tabletop.odor_field
	var sun: SunBeacon = arena.sun_beacon
	var food: FoodPiece = arena.tabletop.food_piece
	
	# Test 1: 3D Odor Field Bilateral Sensing & Ambient Wind
	print("\n[Test 1] Testing 3D Bilateral Odor Sensing & Wind Advection...")
	var fly_start_pos := Vector3(0.0, 0.3, 0.0)
	fly.global_position = fly_start_pos
	fly.rotation = Vector3.ZERO # Facing -Z
	
	var odor_data = odor_field.sample_antennae(fly.global_position, fly.global_transform.basis)
	print("Odor Concentration: ", snapped(odor_data["concentration"], 0.01))
	print("Relative Bearing to Food: ", snapped(rad_to_deg(odor_data["relative_bearing"]), 0.1), " deg")
	print("Ambient Wind Vector: ", odor_data["wind_vector"])
	assert(odor_data["concentration"] > 0.05, "Odor concentration must be detectable")
	assert(odor_data["relative_bearing"] > 0.0, "Food on right must yield positive relative bearing")
	assert(odor_data["c_right"] >= odor_data["c_left"], "Right antenna must detect higher concentration than left")
	assert(odor_data["wind_vector"].length() > 0.05, "Ambient wind vector must be non-zero")
	print("✓ Bilateral antenna gradient detection passed!")
	
	# Test 2: Autonomous In-Plume SURGE Chemotaxis
	print("\n[Test 2] Testing Autonomous In-Plume SURGE Flight...")
	fly.mode = FlyAgent.FlightMode.AUTO_PFL3
	var initial_dist: float = fly.global_position.distance_to(odor_field.food_position)
	print("Initial Distance to Food: ", snapped(initial_dist, 0.01), " m")
	
	# Simulate 90 physics frames (~1.5 seconds)
	for frame in range(90):
		await physics_frame
		
	var final_dist: float = fly.global_position.distance_to(odor_field.food_position)
	print("Final Distance to Food after 90 frames: ", snapped(final_dist, 0.01), " m")
	print("Distance change: ", snapped(final_dist - initial_dist, 0.01), " m")
	print("Navigation State: ", FlyAgent.AutoNavState.keys()[fly.nav_state])
	assert(final_dist < initial_dist, "Autonomous SURGE navigation must steer fly closer to the food source!")
	assert(fly.nav_state == FlyAgent.AutoNavState.SURGE, "In-plume navigation state must be SURGE")
	print("✓ Autonomous PFL3 closed-loop chemotaxis passed!")
	
	# Test 3: Autonomous Lost-Plume CAST Anemotaxis
	print("\n[Test 3] Testing Lost-Plume CAST Crosswind Alternation...")
	# Place fly far outside odor plume
	fly.global_position = Vector3(-1.8, 0.5, 1.8)
	for frame in range(10):
		await physics_frame
	print("Out-of-plume odor conc: ", snapped(fly.odor_strength, 0.01))
	print("Navigation State: ", FlyAgent.AutoNavState.keys()[fly.nav_state])
	assert(fly.nav_state == FlyAgent.AutoNavState.CAST, "Fly outside plume must enter CAST state")
	
	var dir1: float = fly._cast_direction
	# Wait for cast timer to flip direction (> 0.8s = ~50 frames)
	for frame in range(60):
		await physics_frame
	var dir2: float = fly._cast_direction
	print("Cast direction 1: ", dir1, " -> Cast direction 2: ", dir2)
	assert(dir1 != dir2, "Crosswind casting must alternate sweep directions periodically")
	print("✓ Autonomous CAST crosswind sweep alternation passed!")
	
	# Test 4: Celestial Sun Beacon Retinotopic Anchoring & Beam
	print("\n[Test 4] Testing Sun Compass Anchoring & Guidance Beam...")
	sun.set_sun_angle(deg_to_rad(60.0))
	var sun_az: float = sun.get_sun_azimuth()
	print("Sun Azimuth: ", snapped(rad_to_deg(sun_az), 0.1), " deg")
	assert(abs(rad_to_deg(sun_az) - 60.0) < 1.0, "Sun azimuth must match set angle")
	assert(sun._beam_inst != null and sun._beam_inst.visible, "Guidance beam must be instantiated and active")
	print("✓ Celestial Sun beacon navigation & retinotopic beam passed!")
	
	# Test 5: Food Consumption & Energy Replenishment
	print("\n[Test 5] Testing Food Consumption & Metabolic Replenishment...")
	var initial_energy: float = arena.metabolic_energy
	arena._on_food_consumed(food.global_position)
	print("Initial Energy: ", snapped(initial_energy, 0.1), " -> Replenished: ", snapped(arena.metabolic_energy, 0.1))
	print("Food Score: ", arena.food_score)
	assert(arena.food_score >= 1, "Food consumption must increment score")
	assert(arena.metabolic_energy >= initial_energy, "Food consumption must replenish energy")
	print("✓ Food consumption & metabolism passed!")
	
	print("\n===> ALL CLOSED-LOOP NEURO-FLIGHT & ANEMOTAXIS TESTS PASSED! <===")
	quit(0)
