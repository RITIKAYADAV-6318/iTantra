from tts.tts import TTSWrapper

w = TTSWrapper()
w.preload_speakers({'en': 'reference_clips/speaker_mix.wav'})
out = w.synthesize_mixed(
    "Team Alpha यहाँ है। We need मदद at grid reference two eight point five.",
    speaker_wav='reference_clips/speaker_mix.wav'
)
print('Output:', out)