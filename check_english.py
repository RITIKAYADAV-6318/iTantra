# check_english.py
from stt.stt import get_stt_output
r = get_stt_output('demo_outputs/english_baseline.wav')  # adjust path to your actual recording
print("FULL TEXT:", repr(r.text))