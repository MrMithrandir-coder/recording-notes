#!/usr/bin/env python3
"""Transcribe lecture and lab-meeting audio with MLX Whisper."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_DIR / "config.json"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "transcripts"


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration must be a JSON object: {path}")
    return data


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_DIR / path


def load_glossary_prompt(files: Iterable[str], max_chars: int) -> tuple[str, int]:
    terms: list[str] = []
    seen: set[str] = set()

    for filename in files:
        path = resolve_project_path(filename)
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line in seen:
                continue
            terms.append(line)
            seen.add(line)

    prefix = (
        "这是一段大学课程或实验室组会录音，涉及数学、物理、量子信息与"
        "计算机科学。请使用规范简体中文，准确保留英文术语、缩写、变量名、"
        "软件包名称和单位。可能出现的专业词汇包括："
    )
    prompt = prefix + "；".join(terms)
    if len(prompt) > max_chars:
        prompt = prompt[:max_chars].rsplit("；", 1)[0]
    return prompt, len(terms)


def format_timestamp(seconds: float, *, srt: bool = False) -> str:
    milliseconds = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    separator = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalized_segments(result: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for item in result.get("segments") or []:
        text = clean_text(item.get("text"))
        if not text:
            continue
        segment: dict[str, Any] = {
            "id": item.get("id", len(segments)),
            "start": float(item.get("start", 0.0)),
            "end": float(item.get("end", item.get("start", 0.0))),
            "text": text,
        }
        if item.get("words"):
            segment["words"] = item["words"]
        segments.append(segment)
    return segments


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return str(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_duration(path: Path) -> float | None:
    if not shutil.which("ffprobe"):
        return None
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        return float(completed.stdout.strip()) if completed.returncode == 0 else None
    except ValueError:
        return None


def render_timestamped_markdown(
    source: Path, metadata: dict[str, Any], segments: list[dict[str, Any]]
) -> str:
    lines = [
        f"# 转写：{source.stem}",
        "",
        f"- 来源：`{source.name}`",
        f"- 模型：`{metadata['model']}`",
        f"- 语言：`{metadata['detected_language']}`",
        f"- 生成时间：{metadata['created_at']}",
        "",
        "## 带时间戳转写",
        "",
    ]
    for segment in segments:
        stamp = format_timestamp(segment["start"]).split(".", 1)[0]
        lines.append(f"[{stamp}] {segment['text']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_srt(segments: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = format_timestamp(segment["start"], srt=True)
        end = format_timestamp(segment["end"], srt=True)
        blocks.append(f"{index}\n{start} --> {end}\n{segment['text']}")
    return "\n\n".join(blocks).rstrip() + "\n"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def output_paths(output_dir: Path, stem: str) -> dict[str, Path]:
    return {
        "text": output_dir / f"{stem}.txt",
        "timestamps": output_dir / f"{stem}.timestamps.md",
        "srt": output_dir / f"{stem}.srt",
        "json": output_dir / f"{stem}.json",
    }


def doctor() -> int:
    checks = {
        "python": sys.version.split()[0],
        "ffmpeg": shutil.which("ffmpeg") or "missing",
        "ffprobe": shutil.which("ffprobe") or "missing",
        "mlx_whisper": "installed"
        if importlib.util.find_spec("mlx_whisper")
        else "missing",
    }
    for name, value in checks.items():
        print(f"{name}: {value}")
    ready = checks["ffmpeg"] != "missing" and checks["mlx_whisper"] == "installed"
    return 0 if ready else 1


def transcribe_one(
    audio: Path,
    *,
    output_dir: Path,
    model: str,
    language: str | None,
    word_timestamps: bool,
    condition_on_previous_text: bool,
    initial_prompt: str,
    glossary_terms: int,
    force: bool,
) -> dict[str, Path]:
    if not audio.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio}")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required but was not found on PATH")

    paths = output_paths(output_dir, audio.stem)
    collisions = [path for path in paths.values() if path.exists()]
    if collisions and not force:
        joined = ", ".join(str(path) for path in collisions)
        raise FileExistsError(f"Output already exists; use --force to replace it: {joined}")

    import mlx_whisper  # Imported lazily so --doctor works before installation.

    print(f"Transcribing: {audio}", flush=True)
    result = mlx_whisper.transcribe(
        str(audio),
        path_or_hf_repo=model,
        language=language,
        task="transcribe",
        initial_prompt=initial_prompt or None,
        word_timestamps=word_timestamps,
        condition_on_previous_text=condition_on_previous_text,
        verbose=False,
    )
    segments = normalized_segments(result)
    plain_text = clean_text(result.get("text")) or "\n".join(
        segment["text"] for segment in segments
    )
    metadata = {
        "source": str(audio.resolve()),
        "source_sha256": sha256_file(audio),
        "duration_seconds": probe_duration(audio),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": model,
        "requested_language": language or "auto",
        "detected_language": result.get("language") or language or "unknown",
        "word_timestamps": word_timestamps,
        "glossary_terms_loaded": glossary_terms,
    }
    payload = {
        "metadata": metadata,
        "text": plain_text,
        "segments": segments,
    }

    atomic_write_text(paths["text"], plain_text.rstrip() + "\n")
    atomic_write_text(
        paths["timestamps"], render_timestamped_markdown(audio, metadata, segments)
    )
    atomic_write_text(paths["srt"], render_srt(segments))
    atomic_write_text(
        paths["json"],
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n",
    )

    for path in paths.values():
        print(f"Wrote: {path}")
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe lecture or lab-meeting audio with MLX Whisper."
    )
    parser.add_argument("audio", nargs="*", type=Path, help="Audio/video file(s)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--language", help="Language code such as zh/en, or auto")
    parser.add_argument("--force", action="store_true", help="Replace existing outputs")
    parser.add_argument("--doctor", action="store_true", help="Check local dependencies")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.doctor:
        return doctor()
    if not args.audio:
        print("No audio files supplied. See --help.", file=sys.stderr)
        return 2

    config_path = args.config.expanduser().resolve()
    config = load_config(config_path)
    model = args.model or str(config.get("model", "mlx-community/whisper-large-v3-turbo"))
    requested_language = args.language or str(config.get("language", "zh"))
    language = None if requested_language.lower() == "auto" else requested_language
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else DEFAULT_OUTPUT_DIR
    )
    prompt, term_count = load_glossary_prompt(
        config.get("glossary_files", []), int(config.get("max_glossary_chars", 6000))
    )

    failures = 0
    for supplied_path in args.audio:
        audio = supplied_path.expanduser().resolve()
        try:
            transcribe_one(
                audio,
                output_dir=output_dir,
                model=model,
                language=language,
                word_timestamps=bool(config.get("word_timestamps", True)),
                condition_on_previous_text=bool(
                    config.get("condition_on_previous_text", True)
                ),
                initial_prompt=prompt,
                glossary_terms=term_count,
                force=args.force,
            )
        except Exception as exc:
            failures += 1
            print(f"ERROR: {audio}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

