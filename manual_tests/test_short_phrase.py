from tts.tts import TTSWrapper

w = TTSWrapper()
w.preload_speakers({'hi': 'reference_clips/speaker_mix.wav'})
out = w.synthesize('यहाँ है।', 'hi', 'reference_clips/speaker_mix.wav', out_path='_test_short_phrase.wav')
print('Output:', out)