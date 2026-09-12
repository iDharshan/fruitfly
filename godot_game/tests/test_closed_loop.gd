extends SceneTree

## Headless Closed-Loop Neuro-Flight & Autonomous Navigation Test
## Tests:
##  1. 3D Volumetric Odor Field bilateral antenna sampling
##  2. Autonomous PFL3 Chemotaxis gradient ascending (distance decreases)
##  3. Celestial Sun Beacon angle streaming and compass locking

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
	
	# Test 1: 3D Odor Field Bilateral Sensing
	print("\n[Test 1] Testing 3D Bilateral Odor Sensing...")
	var fly_start_pos := Vector3(0.0, 0.3, 0.0)
	fly.global_position = fly_start_pos
	fly.rotation = Vector3.ZERO # Facing -Z
	
	# Food is at (1.2, 0.08, -0.8), so it is to the RIGHT and FORWARD (+X, -Z)
	var odor_data = odor_field.sample_antennae(fly.global_position, fly.global_transform.basis)
	print("Odor Concentration: ", snapped(odor_data["concentration"], 0.01))
	print("Relative Bearing to Food: ", snapped(rad_to_deg(odor_data["relative_bearing"]), 0.1), " deg")
	assert(odor_data["concentration"] > 0.05, "Odor concentration must be detectable")
	assert(odor_data["relative_bearing"] > 0.0, "Food on right must yield positive relative bearing")
	assert(odor_data["c_right"] >= odor_data["c_left"], "Right antenna must detect higher concentration than left")
	print("✓ Bilateral antenna gradient detection passed!")
	
	# Test 2: Autonomous PFL3 Chemotaxis Foraging
	print("\n[Test 2] Testing Autonomous PFL3 Closed-Loop Flight...")
	fly.mode = FlyAgent.FlightMode.AUTO_PFL3
	var initial_dist: float = fly.global_position.distance_to(odor_field.food_position)
	print("Initial Distance to Food: ", snapped(initial_dist, 0.01), " m")
	
	# Simulate 90 physics frames (~1.5 seconds of in-engine flight)
	for frame in range(90):
		await physics_frame
		
	var final_dist: float = fly.global_position.distance_to(odor_field.food_position)
	print("Final Distance to Food after 90 frames: ", snapped(final_dist, 0.01), " m")
	print("Distance change: ", snapped(final_dist - initial_dist, 0.01), " m")
	assert(final_dist < initial_dist, "Autonomous PFL3 navigation must steer fly closer to the food source!")
	print("✓ Autonomous PFL3 closed-loop chemotaxis passed!")
	
	# Test 3: Celestial Sun Beacon Retinotopic Anchoring
	print("\n[Test 3] Testing Sun Compass Anchoring...")
	sun.set_sun_angle(deg_to_rad(60.0))
	var sun_az: float = sun.get_sun_azimuth()
	print("Sun Azimuth: ", snapped(rad_to_deg(sun_az), 0.1), " deg")
	assert(abs(rad_to_deg(sun_az) - 60.0) < 1.0, "Sun azimuth must match set angle")
	print("✓ Celestial Sun beacon navigation passed!")
	
	print("\n===> ALL CLOSED-LOOP NEURO-FLIGHT TESTS PASSED! <===")
	quit(0)
