class_name WingAudioSynthesizer
extends AudioStreamPlayer3D

## Procedural 200 Hz Wingbeat Sound Generator
## Generates a realistic Drosophila wing humming tone with biological harmonics
## (fundamental 200 Hz, 2nd harmonic 400 Hz, 3rd harmonic 600 Hz) and throttle pitch modulation.

var _playback: AudioStreamGeneratorPlayback
var _sample_rate: float = 44100.0
var _phase: float = 0.0
var _base_frequency: float = 200.0
var _current_frequency: float = 200.0
var _target_frequency: float = 200.0
var _amplitude: float = 0.18

func _ready() -> void:
	if DisplayServer.get_name() == "headless":
		return
	var gen := AudioStreamGenerator.new()
	gen.mix_rate = _sample_rate
	gen.buffer_length = 0.1
	stream = gen
	play()
	_playback = get_stream_playback() as AudioStreamGeneratorPlayback

func _exit_tree() -> void:
	stop()
	_playback = null
	stream = null

func set_flight_throttle(throttle: float, is_flying: bool) -> void:
	if not is_flying:
		_target_frequency = 160.0
		_amplitude = 0.04
	else:
		# Throttle modulates from 195 Hz (hover/glide) to 250 Hz (sprint)
		_target_frequency = lerp(195.0, 250.0, clamp(throttle, 0.0, 1.0))
		_amplitude = lerp(0.12, 0.25, clamp(throttle, 0.0, 1.0))

func _process(delta: float) -> void:
	if _playback == null:
		return
		
	_current_frequency = lerp(_current_frequency, _target_frequency, delta * 8.0)
	
	var frames_available: int = _playback.get_frames_available()
	while frames_available > 0:
		var increment: float = _current_frequency / _sample_rate
		_phase = fmod(_phase + increment, 1.0)
		
		# Drosophila wingbeat acoustic waveform:
		# Fundamental (200 Hz) + 2nd harmonic (400 Hz) + subtle 3rd harmonic (600 Hz)
		var t: float = _phase * TAU
		var sample: float = sin(t) * 0.65
		sample += sin(t * 2.0) * 0.25
		sample += sin(t * 3.0) * 0.10
		
		# Subtle amplitude modulation at sub-harmonic representing wing stroke asymmetry
		var am: float = 0.85 + 0.15 * sin(t * 0.5)
		var final_val: float = sample * _amplitude * am
		
		_playback.push_frame(Vector2(final_val, final_val))
		frames_available -= 1
