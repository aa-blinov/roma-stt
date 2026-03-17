"""Post-process raw Whisper output. Infrastructure layer.

Removes common Whisper hallucinations and artefacts, then normalises
capitalisation and trailing punctuation.
"""

import re

# Whisper sometimes hallucinates these fixed phrases regardless of audio content.
_HALLUCINATION_PATTERNS: list[re.Pattern] = [
    # Russian subtitles watermark
    re.compile(r"субтитры\s+(создавал|сделал|by)\s+\S+", re.IGNORECASE),
    re.compile(r"субтитры\s+\w+", re.IGNORECASE),
    # English watermarks / filler tokens
    re.compile(r"\bamara\.org\b", re.IGNORECASE),
    re.compile(r"\bwww\.\S+", re.IGNORECASE),
    re.compile(r"https?://\S+", re.IGNORECASE),
    # Repeated chars / stutter artefacts (e.g. "а-а-а-а", "........")
    re.compile(r"(.)\1{4,}"),
    re.compile(r"(\S{1,3}-){3,}\S{1,3}"),
]

# Tokens that Whisper emits when it detects no speech or non-speech audio.
_SILENCE_TOKENS: frozenset[str] = frozenset({
    "[blank_audio]",
    "[silence]",
    "[music]",
    "[applause]",
    "[noise]",
    "[смех]",
    "(смех)",
    "[музыка]",
    "(музыка)",
    "[тихо]",
    "(тихо)",
    "[аплодисменты]",
    "(аплодисменты)",
})

# Trailing punctuation that already terminates a sentence — don't add a period.
_SENTENCE_ENDINGS = frozenset(".?!…")


def postprocess(text: str) -> str:
    """Clean Whisper output and normalise capitalisation / punctuation.

    Steps:
    1. Strip silence/non-speech tokens.
    2. Remove hallucination phrases.
    3. Capitalise the first letter.
    4. Add a period if the text has no terminal punctuation.
    """
    if not text:
        return text

    cleaned = text.strip()

    # 1. Remove known silence tokens (case-insensitive whole-string match first)
    if cleaned.lower() in _SILENCE_TOKENS:
        return ""

    # Remove silence tokens embedded in longer text
    for token in _SILENCE_TOKENS:
        cleaned = re.sub(re.escape(token), "", cleaned, flags=re.IGNORECASE)

    # 2. Remove hallucination patterns
    for pattern in _HALLUCINATION_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # Collapse multiple spaces / stray punctuation left after removal
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"^[,;:\-–—]+\s*", "", cleaned)  # leading stray punctuation

    if not cleaned:
        return ""

    # 3. Capitalise first letter (leave the rest as-is — Whisper handles casing)
    cleaned = cleaned[0].upper() + cleaned[1:]

    # 4. Add period if the text doesn't already end with sentence punctuation
    if cleaned[-1] not in _SENTENCE_ENDINGS:
        cleaned += "."

    return cleaned
