"""Post-process: Russian hallucination stripping."""

from infrastructure.text_postprocess import postprocess


def test_postprocess_empty_continuation_russian():
    assert postprocess("Продолжение следует...") == ""


def test_postprocess_strips_subtitle_credit():
    assert postprocess("Субтитры добавил DimaTorzok") == ""


def test_postprocess_keeps_normal_sentence():
    out = postprocess("это нормальная фраза")
    assert "нормальная" in out
    assert out.endswith(".")


def test_postprocess_exact_sfx_caption():
    assert postprocess("ВЕСЕЛАЯ МУЗЫКА") == ""
