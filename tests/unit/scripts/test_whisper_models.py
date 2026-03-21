"""scripts/whisper_models.py — каталог и URL."""

from __future__ import annotations

import whisper_models as wm


def test_ordered_keys_match_rows():
    assert wm.ORDERED_MODEL_KEYS == [k for k, _, _ in wm.WHISPER_MODEL_ROWS]


def test_descriptions_cover_all_keys():
    assert set(wm.MODEL_DESCRIPTIONS) == set(wm.ORDERED_MODEL_KEYS)
    for k in wm.ORDERED_MODEL_KEYS:
        assert wm.MODEL_DESCRIPTIONS[k]


def test_compare_hints_cover_all_keys():
    assert set(wm.MODEL_COMPARE_HINTS) == set(wm.ORDERED_MODEL_KEYS)
    for k in wm.ORDERED_MODEL_KEYS:
        assert wm.MODEL_COMPARE_HINTS[k]


def test_model_size_bytes_match_catalog():
    assert set(wm.MODEL_SIZE_BYTES) == set(wm.ORDERED_MODEL_KEYS)
    for k in wm.ORDERED_MODEL_KEYS:
        assert wm.MODEL_SIZE_BYTES[k] > 1_000_000
    assert wm.format_model_size_bytes(wm.MODEL_SIZE_BYTES["tiny"]) != ""


def test_no_duplicate_keys_in_rows():
    keys = [k for k, _, _ in wm.WHISPER_MODEL_ROWS]
    assert len(keys) == len(set(keys))


def test_model_download_url():
    assert wm.model_download_url("tiny") == f"{wm.HF_BASE}/ggml-tiny.bin"
    assert wm.model_download_url("large-v3-turbo-q5_0").endswith("ggml-large-v3-turbo-q5_0.bin")


def test_first_and_last_model_in_expected_tier_order():
    assert wm.ORDERED_MODEL_KEYS[0] == "tiny"
    assert wm.ORDERED_MODEL_KEYS[-1] == "large-v3-turbo-q5_0"
