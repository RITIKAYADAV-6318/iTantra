"""
Criticality Tagger v3 — fixes two real bugs found by testing counter-examples:

1. Callsign regex was matching ANY letters+digits ("Test123", "Hello1"),
   not just real callsigns. Fixed with a NATO phonetic alphabet whitelist.

2. Anti-dilution rule escalated ANY sentence containing a negation word
   to CRITICAL, even harmless ones ("no casualties", "not dangerous").
   Fixed using spaCy's dependency parse (already computed for free) to
   check WHAT the negation modifies:
     - negation attached to a VERB  -> a prohibited action/command
       (e.g. "do not fire") -> stays elevated (HIGH tier)
     - negation attached to a NOUN/ADJ -> a status report/reassurance
       (e.g. "no fire", "not dangerous") -> does NOT auto-escalate

Word-level protection is UNCHANGED: "not"/"no" always score 0.85 so the
allocator never lets them degrade like filler, regardless of which of
the two cases above applies. That was already correct and untouched.

Known, accepted limitation (not fixed, documented instead of faked):
this cannot distinguish "we need help at 28.5N" (operational, urgent)
from "the report discusses coordinates 28.5N" (someone talking ABOUT
coordinates). That requires real intent/discourse classification,
which is out of scope for a regex+POS+dependency system on a 6-day
build. Flag this to your team as a known edge case rather than a bug.
"""

import spacy
import re
import json
import unicodedata

print("Loading AI Language Model (English)...")
try:
    nlp_en = spacy.load("en_core_web_sm")
except OSError:
    raise OSError("spaCy model not found. Run: python -m spacy download en_core_web_sm")

# ============================================================
# PATTERNS
# ============================================================
COORD_PATTERN = re.compile(r"^\d+(?:\.\d+)?[NSWE]$", re.IGNORECASE)
LOCATION_CODE_PATTERN = re.compile(r"^(?:NH|SH|AH|MH|CH)-?\d+$", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")

# FIX: callsigns must use a real phonetic-alphabet word, not any letters.
NATO_ALPHABET = {
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
    "hotel", "india", "juliet", "kilo", "lima", "mike", "november",
    "oscar", "papa", "quebec", "romeo", "sierra", "tango", "uniform",
    "victor", "whiskey", "xray", "x-ray", "yankee", "zulu"
}
NUMBER_WORDS_EN = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"}
CALLSIGN_PATTERN = re.compile(r"^([A-Za-z]+)-?(\d+)$")

def is_callsign(word: str) -> bool:
    """Handles the WRITTEN/joined form: 'Bravo-2' as one token."""
    m = CALLSIGN_PATTERN.match(word)
    if not m:
        return False
    return m.group(1).lower() in NATO_ALPHABET

def find_spoken_callsign_spans(doc):
    """
    Handles the SPOKEN form: real STT output almost never joins
    'bravo' and '2' with a hyphen — a speaker says "bravo two" and
    the ASR emits two separate tokens. Confirmed by testing:
    'bravo 2 requesting backup' silently dropped from HIGH to MEDIUM
    before this existed.

    FIX (v4): this used to only look at ONE pair (tokens[i], tokens[i+1]),
    so a multi-digit spoken callsign like "bravo two five" (Bravo-25)
    only tagged "bravo" and "two" as CALLSIGN — "five" fell through to
    the plain NUMBER branch (0.70 instead of 0.90). Sentence-level
    priority still came out HIGH either way (the tag list just needs
    ONE "CALLSIGN" entry to trigger that tier), which is exactly why
    this didn't show up in the test table — but if the allocator uses
    per-word scores, part of the callsign got less bit-protection than
    the rest of it. Fixed with a sliding window that consumes ALL
    consecutive digit-words after the phonetic-alphabet word, not just
    the first one.
    """
    span_indices = set()
    tokens = list(doc)
    i = 0
    while i < len(tokens):
        w1 = tokens[i].text.lower()
        if w1 in NATO_ALPHABET:
            j = i + 1
            consumed_any = False
            while j < len(tokens):
                wj = tokens[j].text
                if wj.isdigit() or wj.lower() in NUMBER_WORDS_EN:
                    span_indices.add(tokens[j].i)
                    consumed_any = True
                    j += 1
                else:
                    break
            if consumed_any:
                span_indices.add(tokens[i].i)
                i = j
                continue
        i += 1
    return span_indices

# ============================================================
# DICTIONARIES
# ============================================================
CRITICAL_WORDS_EN = {
    "help", "emergency", "injured", "injury", "fire", "attack", "casualty",
    "casualties", "evacuate", "enemy", "danger", "target", "immediately",
    "urgent", "rescue", "trapped", "sos", "mayday", "explosion", "crash"
}
# NOTE: a hand-rolled NEGATION_WORDS_EN set used to live here but was never
# referenced anywhere in the code (dead code, caught in review) — negation
# is detected structurally via spaCy's dependency parse (token.dep_=="neg")
# instead, plus an explicit override for "never" (see find_negation_map and
# _tag_english) since spaCy's parser handles that word inconsistently in
# short imperative sentences.

NUMBER_WORDS_HI = {"एक", "दो", "तीन", "चार", "पाँच", "पांच", "छह", "छः", "सात", "आठ", "नौ", "दस"}
CRITICAL_WORDS_HI = {
    "मदद", "बचाओ", "आपातकाल", "घायल", "चोट", "खून", "आग", "धमाका",
    "हमला", "दुश्मन", "हताहत", "मौत", "खतरा", "निशाना", "तुरंत", "फौरन", "बचाव"
}
NEGATION_WORDS_HI = {"नहीं", "मत", "ना", "न"}
EVACUATION_WORDS_HI = {"निकासी", "निकालो", "बाहर"}
STOPWORDS_HI = {"और", "है", "हैं", "था", "थे", "थी", "को", "में", "से", "के", "का", "की", "यह", "वह", "हम", "तुम", "आप", "पर", "भी", "ही", "तो", "ने"}
CRITICAL_PHRASES_HI = ["मदद करो", "मदद चाहिए", "जान का खतरा", "खाली करो", "तुरंत मदद"]

# FIX (v4): Hindi previously had NO spoken-callsign detection at all —
# NATO_ALPHABET was Latin-only. Common transliterations added here so a
# callsign spoken in a Hindi utterance ("ब्रावो दो", i.e. "Bravo two")
# is recognized the same way the English spoken form is. This is a
# best-effort transliteration list, not exhaustive — spellings can vary
# across speakers/regions, so treat this as a starting point to expand
# once you hear your team's actual demo audio, the same way the English
# dictionaries were expanded after testing real sentences.
NATO_ALPHABET_HI = {
    "अल्फा": "alpha", "ब्रावो": "bravo", "चार्ली": "charlie", "डेल्टा": "delta",
    "इको": "echo", "फॉक्सट्रॉट": "foxtrot", "गोल्फ": "golf", "होटल": "hotel",
    "इंडिया": "india", "जूलियट": "juliet", "किलो": "kilo", "लीमा": "lima",
    "माइक": "mike", "नवंबर": "november", "ऑस्कर": "oscar", "पापा": "papa",
    "क्यूबेक": "quebec", "रोमियो": "romeo", "सिएरा": "sierra", "टैंगो": "tango",
    "यूनिफॉर्म": "uniform", "विक्टर": "victor", "व्हिस्की": "whiskey",
    "एक्सरे": "xray", "यांकी": "yankee", "जूलू": "zulu"
}

def find_spoken_callsign_spans_hi(words: list) -> set:
    """
    Hindi equivalent of find_spoken_callsign_spans: a NATO-alphabet
    word (transliterated) followed by one or more number words/digits
    is a spoken callsign, e.g. "ब्रावो दो" (Bravo two).
    """
    span_indices = set()
    i = 0
    while i < len(words):
        if words[i] in NATO_ALPHABET_HI:
            j = i + 1
            consumed_any = False
            while j < len(words):
                if words[j].isdigit() or words[j] in NUMBER_WORDS_HI:
                    span_indices.add(j)
                    consumed_any = True
                    j += 1
                else:
                    break
            if consumed_any:
                span_indices.add(i)
                i = j
                continue
        i += 1
    return span_indices

# ============================================================
# HELPERS
# ============================================================
def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()

def clean_hindi_token(token: str) -> str:
    punctuation = "।,.!?;:()[]{}\"'\u201c\u201d\u2018\u2019-"
    return token.strip(punctuation)

def detect_special_token(word: str):
    if COORD_PATTERN.fullmatch(word): return 1.0, "COORDINATE"
    if LOCATION_CODE_PATTERN.fullmatch(word): return 0.90, "LOCATION_CODE"
    if is_callsign(word): return 0.90, "CALLSIGN"
    if NUMBER_PATTERN.fullmatch(word): return 0.70, "NUMBER"
    return None

def resolve_negation_target(neg_token):
    """
    Walks the dependency tree to find what a negation word actually
    modifies. Handles the common case where 'not' attaches to an
    auxiliary verb ("is not dangerous") by checking that verb's own
    children for the real predicate (acomp/attr/dobj/xcomp).
    """
    head = neg_token.head
    if head.pos_ == "AUX":
        for child in head.children:
            if child.dep_ in ("acomp", "attr", "dobj", "xcomp") and child != neg_token:
                return child
    return head

def is_command_negation(neg_token_lower: str, target) -> bool:
    """
    Shared classification logic used by BOTH find_negation_map and
    _tag_english. FIX (v4): this same condition used to be written out
    independently in two places — they agreed today, but nothing
    enforced that, so an edit to one without the other would silently
    drift them apart. Now there's exactly one place this rule lives.
    """
    return (neg_token_lower == "never") or (target.pos_ == "VERB")

def find_negation_map(doc):
    """
    First pass over the sentence: find every negation word AND the
    specific token it negates. Returns {token_index: "COMMAND"|"STATUS"}
    for the TARGET tokens (e.g. "fire" in "do not fire"), separate from
    the negation words themselves ("not"/"no").

    This exists because a target word like "fire" is ALSO a dictionary
    entry in CRITICAL_WORDS_EN — without this map, "fire" would get
    tagged URGENT on its own merits regardless of being negated, which
    is exactly the bug: "do not fire" and "there is no fire" both
    re-triggered CRITICAL through the target word, not the negation word.
    """
    target_map = {}
    for token in doc:
        is_neg = (
            token.dep_ == "neg"
            or (token.pos_ == "DET" and token.text.lower() == "no")
            or token.text.lower() == "never"
        )
        if is_neg:
            target = resolve_negation_target(token)
            is_command = is_command_negation(token.text.lower(), target)
            target_map[target.i] = "COMMAND" if is_command else "STATUS"
    return target_map

# ============================================================
# ENGLISH TAGGER
# ============================================================
def _tag_english(text: str) -> list:
    doc = nlp_en(text)
    negated_targets = find_negation_map(doc)
    spoken_callsign_spans = find_spoken_callsign_spans(doc)
    results = []

    for token in doc:
        if token.is_punct or token.is_space:
            continue

        word, lower_word = token.text, token.text.lower()
        special = detect_special_token(word)
        is_negation = (
            token.dep_ == "neg"
            or (token.pos_ == "DET" and lower_word == "no")
            # FIX: short imperative negations ("Never fire.") get mis-parsed
            # by spaCy's parser — "fire" comes back tagged NOUN instead of
            # VERB, which flipped this into the wrong (lower-priority)
            # bucket. Catching "never" by lemma directly, independent of
            # the parser's POS call for the target, fixes this specific
            # short-sentence failure mode confirmed by testing.
            or lower_word == "never"
        )

        if token.i in spoken_callsign_spans:
            score, tag = 0.90, "CALLSIGN"
        elif special:
            score, tag = special
        elif is_negation:
            target = resolve_negation_target(token)
            if is_command_negation(lower_word, target):
                score, tag = 0.90, "NEGATED_COMMAND"
            else:
                score, tag = 0.85, "NEGATED_STATUS"
        elif token.i in negated_targets:
            if negated_targets[token.i] == "COMMAND":
                score, tag = 0.75, "NEGATED_TARGET_COMMAND"
            else:
                score, tag = 0.35, "NEGATED_TARGET_STATUS"
        elif lower_word in CRITICAL_WORDS_EN:
            score, tag = 1.0, "URGENT"
        elif token.pos_ == "NUM":
            score, tag = 0.70, "NUMBER"
        elif token.ent_type_ in {"PERSON", "LOC", "GPE", "ORG"}:
            score, tag = 0.75, "ENTITY"
        elif token.is_stop:
            score, tag = 0.10, "FILLER"
        else:
            score, tag = 0.30, "NEUTRAL"

        results.append({"word": word, "criticality_score": score, "tag": tag})
    return results

# ============================================================
# HINDI TAGGER (no reliable dependency parser available, so we use
# a cheap proximity heuristic instead: a negation next to a critical
# word is a negated command; a standalone negation elsewhere is not)
# ============================================================
def _tag_hindi(text: str) -> list:
    """
    No reliable dependency parser exists for Hindi in spaCy's small
    models, so this uses a proximity heuristic instead: a negation
    within 2 words of a critical word is treated as negating it.

    Same two-pass structure as English: first find which word indices
    are negation TARGETS, so those words don't also independently fire
    their own CRITICAL_WORDS_HI dictionary tag (the same bug as "fire"
    in the English version, fixed here symmetrically).
    """
    raw_words = [clean_hindi_token(w) for w in normalize_text(text).split()]
    raw_words = [w for w in raw_words if w]

    spoken_callsign_spans = find_spoken_callsign_spans_hi(raw_words)

    # Pass 1: find negation words and the nearest critical word they negate
    negated_targets = {}  # index -> "COMMAND" (heuristic: no verb info in Hindi, so
                            #                   we just call any negated critical word HIGH-tier)
    for i, w in enumerate(raw_words):
        if w in NEGATION_WORDS_HI:
            window = list(range(max(0, i - 2), i)) + list(range(i + 1, min(len(raw_words), i + 3)))
            for j in window:
                if raw_words[j] in CRITICAL_WORDS_HI:
                    negated_targets[j] = "COMMAND"

    results = []
    for i, clean in enumerate(raw_words):
        special = detect_special_token(clean)
        is_negation = clean in NEGATION_WORDS_HI

        if i in spoken_callsign_spans:
            score, tag = 0.90, "CALLSIGN"
        elif special:
            score, tag = special
        elif is_negation:
            score, tag = (0.90, "NEGATED_COMMAND") if any(
                raw_words[j] in CRITICAL_WORDS_HI
                for j in range(max(0, i - 2), min(len(raw_words), i + 3)) if j != i
            ) else (0.85, "NEGATED_STATUS")
        elif i in negated_targets:
            # This word is being negated by a nearby negation word — don't
            # let it also independently fire URGENT.
            score, tag = 0.75, "NEGATED_TARGET_COMMAND"
        elif clean in CRITICAL_WORDS_HI:
            score, tag = 1.0, "URGENT"
        elif clean in EVACUATION_WORDS_HI:
            score, tag = 0.90, "EVACUATION"
        elif clean.isdigit() or clean in NUMBER_WORDS_HI:
            score, tag = 0.70, "NUMBER"
        elif clean in STOPWORDS_HI:
            score, tag = 0.10, "FILLER"
        else:
            score, tag = 0.30, "NEUTRAL"

        results.append({"word": clean, "criticality_score": score, "tag": tag})
    return results

# ============================================================
# PACKET-LEVEL PRIORITY (word score != sentence priority — kept as
# two clearly separate concepts, per the tiering below)
# ============================================================
def calculate_overall_priority(word_scores: list) -> tuple:
    if not word_scores:
        return 0.0, "LOW"

    tags = [item["tag"] for item in word_scores]

    if "COORDINATE" in tags or "URGENT" in tags:
        return 0.95, "CRITICAL"
    if "CALLSIGN" in tags or "LOCATION_CODE" in tags or "EVACUATION" in tags or "NEGATED_COMMAND" in tags:
        return 0.80, "HIGH"
    if "ENTITY" in tags or "NUMBER" in tags or "NEGATED_STATUS" in tags:
        return 0.60, "MEDIUM"

    avg_score = sum(item["criticality_score"] for item in word_scores) / len(word_scores)
    if avg_score >= 0.5:
        return round(avg_score, 2), "MEDIUM"
    return round(avg_score, 2), "LOW"

# ============================================================
# MAIN EXPORT
# ============================================================
def assign_criticality(text: str, lang: str = "en") -> dict:
    if lang not in {"en", "hi"}:
        raise ValueError(f"lang must be 'en' or 'hi', got {lang!r}")
    text = normalize_text(text)
    if lang == "hi":
        word_scores = _tag_hindi(text)
        detected_phrases = [p for p in CRITICAL_PHRASES_HI if p in text]
    else:
        word_scores = _tag_english(text)
        detected_phrases = []

    overall_score, priority = calculate_overall_priority(word_scores)
    return {
        "original_text": text,
        "language": lang.upper(),
        "total_tokens": len(word_scores),
        "packet_priority": priority,
        "priority_score": overall_score,
        "detected_phrases": detected_phrases,
        "tokens": word_scores
    }

# ============================================================
# TESTS — every sentence from the critique's expectation table
# ============================================================
if __name__ == "__main__":
    # (sentence, lang, expected_priority, expect_callsign_tag)
    cases = [
        # --- ENGLISH ---
        ("Fire!", "en", "CRITICAL", None),
        ("Help immediately!", "en", "CRITICAL", None),
        ("We need help at 28.5N.", "en", "CRITICAL", None),
        ("Bravo-2 requesting backup.", "en", "HIGH", True),        # written/hyphenated form
        ("bravo 2 requesting backup", "en", "HIGH", True),         # spoken/ASR form, no hyphen
        ("bravo two five requesting backup", "en", "HIGH", True),  # FIX (v4): multi-digit spoken callsign
        ("Do not fire.", "en", "HIGH", None),
        ("Never fire.", "en", "HIGH", None),
        ("Cannot fire.", "en", "HIGH", None),
        ("There is no fire.", "en", "MEDIUM", None),
        ("There are no casualties.", "en", "MEDIUM", None),
        ("The training exercise is not dangerous.", "en", "MEDIUM", None),
        ("The weather is good today.", "en", "LOW", None),
        ("This is Test123 unit online.", "en", None, False),       # must NOT be a callsign

        # --- HINDI (FIX v4: previously zero automated coverage) ---
        ("आग!", "hi", "CRITICAL", None),                                    # "Fire!"
        ("तुरंत मदद चाहिए।", "hi", "CRITICAL", None),                        # "Help needed immediately"
        ("हमें 28.5N पर मदद चाहिए।", "hi", "CRITICAL", None),                # coordinate + urgent word
        ("ब्रावो दो सहायता मांग रहा है।", "hi", "HIGH", True),               # FIX (v4): spoken Hindi callsign
        # Known, documented limitation: Hindi has no dependency parser, so
        # unlike English it can't tell a prohibited command from a status
        # report/reassurance — every negated-critical-word case lands in
        # the same HIGH tier here, even though "no danger" is genuinely
        # less urgent than "do not fire" would be. Flagged, not silently
        # papered over.
        ("यहाँ कोई खतरा नहीं है।", "hi", "HIGH", None),                     # "there is no danger here"
    ]

    failures = 0
    for sentence, lang, expected_priority, expect_callsign in cases:
        result = assign_criticality(sentence, lang)
        callsign_hit = any(t["tag"] == "CALLSIGN" for t in result["tokens"])

        ok = True
        if expected_priority is not None and result["packet_priority"] != expected_priority:
            ok = False
        if expect_callsign is not None and callsign_hit != expect_callsign:
            ok = False

        status = "PASS" if ok else "FAIL"
        failures += (0 if ok else 1)
        print(f"[{status}] ({lang}) {sentence!r:38s} -> priority={result['packet_priority']:9s} "
              f"callsign={callsign_hit}  (expected priority={expected_priority}, callsign={expect_callsign})")

    print(f"\n{len(cases) - failures}/{len(cases)} passed.")
    if failures:
        raise SystemExit(f"{failures} test case(s) FAILED — fix before merging.")

    # Extra check for the multi-digit callsign fix specifically: confirm
    # EVERY digit word in "bravo two five" got tagged CALLSIGN, not just
    # the first one.
    r = assign_criticality("bravo two five requesting backup", "en")
    callsign_words = [t["word"] for t in r["tokens"] if t["tag"] == "CALLSIGN"]
    assert callsign_words == ["bravo", "two", "five"], (
        f"Expected all three callsign tokens tagged, got: {callsign_words}"
    )
    print("Multi-digit callsign check passed:", callsign_words)