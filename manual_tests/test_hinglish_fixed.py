# test_hinglish_fixed.py
from tts.tts import TTSWrapper, _split_by_language

# First, just check the splitting logic itself — no synthesis yet
text = "Team Alpha यहाँ है। We need मदद at grid reference two eight point five."
print("Runs after merge:")
for chunk, lang in _split_by_language(text):
    print(f"  [{lang}] {chunk!r}")

w = TTSWrapper()
w.preload_speakers({'en': 'reference_clips/speaker_mix.wav'})
out = w.synthesize_mixed(text, speaker_wav='reference_clips/speaker_mix.wav', out_path='_test_hinglish_fixed.wav')
print('Output:', out)