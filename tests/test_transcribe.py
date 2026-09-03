import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "transcribe.py"
SPEC = importlib.util.spec_from_file_location("transcribe", SCRIPT)
assert SPEC and SPEC.loader
transcribe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transcribe)


class TimestampTests(unittest.TestCase):
    def test_markdown_timestamp(self):
        self.assertEqual(transcribe.format_timestamp(3723.456), "01:02:03.456")

    def test_srt_timestamp_rounds(self):
        self.assertEqual(
            transcribe.format_timestamp(1.9996, srt=True), "00:00:02,000"
        )

    def test_negative_timestamp_is_clamped(self):
        self.assertEqual(transcribe.format_timestamp(-1), "00:00:00.000")


class RenderTests(unittest.TestCase):
    def test_srt_rendering(self):
        segments = [{"start": 0.0, "end": 1.25, "text": "量子比特"}]
        self.assertEqual(
            transcribe.render_srt(segments),
            "1\n00:00:00,000 --> 00:00:01,250\n量子比特\n",
        )

    def test_segments_drop_empty_text(self):
        result = {
            "segments": [
                {"id": 0, "start": 0, "end": 1, "text": "  "},
                {"id": 1, "start": 1, "end": 2, "text": "  梯度   下降 "},
            ]
        }
        self.assertEqual(
            transcribe.normalized_segments(result),
            [{"id": 1, "start": 1.0, "end": 2.0, "text": "梯度 下降"}],
        )


class GlossaryTests(unittest.TestCase):
    def test_glossary_deduplicates_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.txt"
            second = Path(directory) / "second.txt"
            first.write_text("# comment\nHilbert space\nQAOA\n", encoding="utf-8")
            second.write_text("QAOA\nVQE\n", encoding="utf-8")
            prompt, count = transcribe.load_glossary_prompt(
                [str(first), str(second)], 1000
            )
        self.assertEqual(count, 3)
        self.assertEqual(prompt.count("QAOA"), 1)
        self.assertIn("Hilbert space", prompt)
        self.assertIn("VQE", prompt)


if __name__ == "__main__":
    unittest.main()

