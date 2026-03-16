"""Domain: STT engine interface contract."""

from domain.interfaces import STTEngine


class TestSTTEngineProtocol:
    """STTEngine must have transcribe(audio_path) -> str."""

    def test_engine_with_transcribe_satisfies_protocol(self):
        class FakeEngine:
            def transcribe(self, audio_path: str) -> str:
                return "Hello, world."

        engine = FakeEngine()
        assert isinstance(engine, STTEngine)
        assert engine.transcribe("dummy.wav") == "Hello, world."

    def test_engine_must_return_str(self):
        class FakeEngine:
            def transcribe(self, audio_path: str) -> str:
                return ""

        result = FakeEngine().transcribe("x.wav")
        assert isinstance(result, str)
