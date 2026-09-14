TEST_CASES = [
    {
        "file": "test_audio/medical_1.m4a",
        "expected": "Need immediate medical assistance at checkpoint Bravo"
    },
    {
        "file": "test_audio/backup_1.m4a",
        "expected": "Send backup to grid reference 4729"
    }
]

from stt.stt import get_stt_output

passed = 0

for tc in TEST_CASES:

    result = get_stt_output(tc["file"])

    print("Expected:", tc["expected"])
    print("Got     :", result.text)

    if tc["expected"].lower() in result.text.lower():
        passed += 1

print(f"\nPassed {passed}/{len(TEST_CASES)}")