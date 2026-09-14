from channel.sound_events import _load_audio, _get_classifier, _chunk_audio

path = "reference_clips/speaker_gunen.wav"   # your standalone gunshot-only file

audio, sample_rate = _load_audio(path)
print(f"Duration: {len(audio) / sample_rate:.2f} seconds, sample rate: {sample_rate}")

chunks = _chunk_audio(audio, sample_rate)
print(f"Number of chunks: {len(chunks)}")

classifier = _get_classifier()

for i, chunk in enumerate(chunks):
    predictions = classifier(
        {"array": chunk, "sampling_rate": sample_rate},
        top_k=5,
        function_to_apply="sigmoid",
    )
    print(f"\n--- Chunk {i} (top 5 raw predictions, unfiltered) ---")
    for p in predictions:
        print(f"  {p['label']:40s} {p['score']:.4f}")