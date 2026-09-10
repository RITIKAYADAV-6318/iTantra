"""
Dashboard — owner: [Integration/UI Lead name]

Plan:
- Streamlit is fastest for a hackathon. Swap to React only if you have spare time.
- Must show, live: detected language, bitrate meter, packet size vs raw size,
  a "normal call" vs "iTantra mode" toggle, and a draggable bitrate slider.
- The bitrate-slider moment (drag down, watch critical words survive) is the
  single most important demo beat. Build the plumbing for it early, polish visuals last.

Run: streamlit run dashboard.py
"""

import streamlit as st

# These imports assume you run this from the repo root, or adjust sys.path.
# from stt.stt import transcribe
# from allocator.criticality import tag_criticality
# from allocator.allocate import allocate
# from channel.simulator import send, send_raw_audio
# from tts.tts import synthesize

st.title("iTantra — Live Demo Dashboard")

mode = st.radio("Mode", ["Normal voice call (baseline)", "iTantra mode"])
bitrate = st.slider("Simulated channel bitrate (kbps)", min_value=0.5, max_value=20.0,
                     value=5.0, step=0.5)
noise = st.slider("Channel noise level", min_value=0.0, max_value=1.0, value=0.3, step=0.05)

st.write(f"Mode: **{mode}** | Bitrate: **{bitrate} kbps** | Noise: **{noise}**")

# STUB — wire real pipeline calls here once modules are ready.
st.info("Wire STT -> allocator -> channel -> TTS calls here. "
        "Show: detected language, packet size vs raw size, protection per word.")

if st.button("Run demo sentence"):
    st.write("Placeholder: run pipeline and play resulting audio here.")
