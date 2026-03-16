"""Domain: config validation — only multilingual models allowed."""

import pytest

from domain.config_validation import (
    is_multilingual_model_path,
    validate_model_path,
)


class TestIsMultilingualModelPath:
    """Accept multilingual/turbo paths; reject en-only."""

    def test_accepts_multilingual_large_v3(self):
        assert is_multilingual_model_path("models/ggml-large-v3.ggml") is True
        assert is_multilingual_model_path("models/ggml-large-v3-turbo.ggml") is True

    def test_accepts_medium_multilingual(self):
        assert is_multilingual_model_path("C:/data/ggml-medium.bin") is True

    def test_rejects_en_ggml_suffix(self):
        assert is_multilingual_model_path("models/ggml-base-en.ggml") is False
        assert is_multilingual_model_path("path/to/model-en.ggml") is False

    def test_rejects_en_bin_suffix(self):
        assert is_multilingual_model_path("model-en.bin") is False

    def test_rejects_en_only_marker(self):
        assert is_multilingual_model_path("models/en-only-large.ggml") is False

    def test_rejects_empty_path(self):
        assert is_multilingual_model_path("") is False

    def test_accepts_path_object(self):
        from pathlib import Path

        assert is_multilingual_model_path(Path("models/ggml-medium.ggml")) is True
        assert is_multilingual_model_path(Path("models/base-en.ggml")) is False


class TestValidateModelPath:
    """validate_model_path raises for en-only."""

    def test_does_not_raise_for_multilingual(self):
        validate_model_path("models/ggml-large-v3.ggml")
        validate_model_path("models/ggml-turbo.ggml")

    def test_raises_for_en_only(self):
        with pytest.raises(ValueError, match="English-only|not allowed"):
            validate_model_path("models/ggml-base-en.ggml")
        with pytest.raises(ValueError, match="English-only|not allowed"):
            validate_model_path("model-en.bin")
