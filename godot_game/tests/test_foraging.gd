extends SceneTree

## Diagnostic test to benchmark autonomous food finding over 10 consecutive spawns
func _init() -> void:
	process_frame.connect(_run_test, CONNECT_ONE_SHOT)

func _run_test() -> void:
	print("--- Benchmarking Autonomous Foraging Over 10 Food Pellets ---")
	var arena_scene: PackedScene = load("res://scenes/main_arena.tscn")
	var arena: MainArena = arena_scene.instantiate() as MainArena
	root.add_child(arena)
	
	for k in range(5):
		await physics_frame
		
	var fly: FlyAgent = arena.fly_agent
	var food: FoodPiece = arena.tabletop.food_piece
	var odor: VolumetricOdorField = arena.tabletop.odor_field
	
	fly.mode = FlyAgent.FlightMode.AUTO_PFL3
	
	var target_eats := 10
	var max_frames_per_food := 400
	var total_frames := 0
	var success_eats := 0
	
	for i in range(target_eats):
		var start_score := arena.food_score
		var start_frame := total_frames
		var initial_dist: float = fly.global_position.distance_to(food.global_position)
		print("\n[Pellet %d] Spawning at %s | Fly at %s (Dist: %5.2f m)" % [
			i + 1, food.global_position, fly.global_position, initial_dist
		])
		
		var reached := false
		while total_frames - start_frame < max_frames_per_food:
			await physics_frame
			total_frames += 1
			if arena.food_score > start_score:
				reached = true
				success_eats += 1
				var frames_taken := total_frames - start_frame
				print("  -> Pellet %d consumed in %d frames (%5.2f s)! Fly at %s" % [
					i + 1, frames_taken, frames_taken / 60.0, fly.global_position
				])
				break
				
		if not reached:
			print("  -> FAILED to reach pellet %d within %d frames! Current dist: %5.2f m, Fly at %s" % [
				i + 1, max_frames_per_food, fly.global_position.distance_to(food.global_position), fly.global_position
			])
	
	print("\n" + "=".repeat(60))
	print("RESULTS: Consumed %d / %d pellets in %d total frames" % [success_eats, target_eats, total_frames])
	print("=".repeat(60))
	arena.queue_free()
	quit(0)
