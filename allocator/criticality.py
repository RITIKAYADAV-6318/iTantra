"""
Criticality tagger — owner: [Allocator Lead name]

Contract:
    tag_criticality(text) -> criticality_per_token (aligned with text.split())

Plan:
- Day 3: regex/dictionary pass is enough. Do NOT overbuild with a full NER model.
  Flag: numbers, coordinates, names/callsigns, negations ("not", "no", "never").
"""

import re
from typing import List

NEGATIONS = {"not", "no", "never", "cannot", "can't", "won't"}

# Simple heuristics — extend the pattern list, don't rebuild the approach.
NUMBER_PATTERN = re.compile(r"\d")


def tag_criticality(text: str) -> List[float]:
    """
    Returns one criticality score [0,1] per whitespace token in `text`.
    1.0 = must survive (number/coordinate/negation), 0.0 = filler.
    """
    tokens = text.split()
    scores = []
    for tok in tokens:
        clean = tok.strip(".,!?").lower()
        if NUMBER_PATTERN.search(clean):
            scores.append(1.0)
        elif clean in NEGATIONS:
            scores.append(0.9)
        elif clean[:1].isupper() and len(clean) > 1:
            # crude "looks like a name" heuristic — refine with a real list if time allows
            scores.append(0.7)
        else:
            scores.append(0.2)
    return scores


if __name__ == "__main__":
    text = "Send backup to grid reference 4729"
    print(tag_criticality(text))
