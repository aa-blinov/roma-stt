"""Post-process raw Whisper output. Infrastructure layer.

Removes common Whisper hallucinations and artefacts, then normalises
capitalisation and trailing punctuation.

Russian phrase list is largely aligned with community-reported outputs on noise/silence
(Whisper large-v2, ~13 h): https://gist.github.com/waveletdeboshir/8bf52f04bf78018194f25b2390c08309
Plus typical subtitle / «продолжение» templates seen on GitHub discussions around Whisper.
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

# Russian templates (substring removal; case-insensitive).
_RU_HALLUCINATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"продолжение\s+следует\.?\.?\.?", re.IGNORECASE),
    re.compile(r"смотрите\s+продолжение\b.*", re.IGNORECASE),
    re.compile(r"спасибо\s+за\s+субтитры!?\.?", re.IGNORECASE),
    re.compile(r"субтитры\s+добавил\b.*", re.IGNORECASE),
    re.compile(r"субтитры\s+подогнал\b.*", re.IGNORECASE),
    re.compile(r"редактор\s+субтитров\b.*", re.IGNORECASE),
    re.compile(r"корректор\s+[а-яё]\.[а-яё]+[а-яё]*\b.*", re.IGNORECASE),
    re.compile(r"\bдима\s*торзок\b.*", re.IGNORECASE),
    re.compile(r"\bdimatorzok\b.*", re.IGNORECASE),
    re.compile(r"подпишись(?:\s+на\s+канал)?!?\.?", re.IGNORECASE),
    re.compile(r"по\s+громкоговорител[юя]\b.*", re.IGNORECASE),
    re.compile(r"по\s+тв\.?\b.*", re.IGNORECASE),
]

# If the whole transcript equals one of these (after strip + casefold), drop it.
# Synced with gist above + common SFX captions in Russian.
_RU_EXACT_HALLUCINATION_PHRASES_LOWER: frozenset[str] = frozenset(
    line.strip().lower()
    for line in """
веселая музыка
спокойная музыка
грустная мелодия
лирическая музыка
динамичная музыка
таинственная музыка
торжественная музыка
интригующая музыка
напряженная музыка
печальная музыка
тревожная музыка
музыкальная заставка
перестрелка
гудок поезда
рёв мотора
шум двигателя
сигнал автомобиля
лай собак
пес лает
кашель
выстрелы
шум дождя
песня
по громкоговорителю
по громкоговорческом языке
взрыв
шум мотора
плеск воды
гудок автомобиля
лай собаки
по тв.
аплодисменты
городской шум
полиция
городской гудок
сигнал машины
смех
стук в дверь
полицейская сирена
звонок в дверь
подпишись на канал
подпишись!
подпишись
поехали!
поехали.
девушки отдыхают...
🦜
💥
😎
🤨
🤔
""".strip().splitlines()
    if line.strip()
)

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

    # Whole line is a known Russian noise caption (gist / common hallucinations)
    if cleaned.casefold() in _RU_EXACT_HALLUCINATION_PHRASES_LOWER:
        return ""

    # Remove silence tokens embedded in longer text
    for token in _SILENCE_TOKENS:
        cleaned = re.sub(re.escape(token), "", cleaned, flags=re.IGNORECASE)

    # 2. Remove hallucination patterns (generic + Russian)
    for pattern in _HALLUCINATION_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    for pattern in _RU_HALLUCINATION_PATTERNS:
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
