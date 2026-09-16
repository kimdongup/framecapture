"""Responsive local web dashboard for the unified pipeline."""

from __future__ import annotations

import os
import platform
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from video_ocr import PipelineOptions, VideoOCRPipeline

BASE = Path(__file__).resolve().parent


def writable_data_dir() -> Path:
    """Use the project folder in development and OS app-data after packaging."""
    if not getattr(sys, "frozen", False):
        return BASE
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "FlowTextCapture"
    if platform.system() == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "FlowTextCapture"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "flowtextcapture"


DATA_ROOT = writable_data_dir()
UPLOADS = DATA_ROOT / "uploads"
OUTPUTS = DATA_ROOT / "outputs"
UPLOADS.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def update(job_id: str, **values) -> None:
    with jobs_lock:
        jobs[job_id].update(values)


def process(job_id: str, source: Path, options: PipelineOptions) -> None:
    try:
        pipeline = VideoOCRPipeline(options)
        result = pipeline.run(source, OUTPUTS, lambda message, value: update(job_id, message=message, progress=round(value * 100)))
        update(job_id, status="done", message="텍스트 추출 완료", progress=100, result=result.name)
    except Exception as exc:
        update(job_id, status="error", message=str(exc))
    finally:
        source.unlink(missing_ok=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/jobs")
def create_job():
    uploaded = request.files.get("video")
    if not uploaded or not uploaded.filename:
        return jsonify(error="동영상 파일을 선택하세요."), 400
    job_id = uuid.uuid4().hex
    suffix = Path(secure_filename(uploaded.filename)).suffix.lower() or ".mp4"
    source = UPLOADS / f"{job_id}{suffix}"
    uploaded.save(source)
    try:
        end_value = request.form.get("end", "").strip()
        options = PipelineOptions(
            start=float(request.form.get("start", 0)),
            end=float(end_value) if end_value else None,
            sample_interval=float(request.form.get("interval", 0)),
            similarity=float(request.form.get("similarity", 0.98)),
            language=request.form.get("language", "ko,en"),
            ocr_engine=request.form.get("engine", "auto"),
            spellcheck=request.form.get("spellcheck") == "on",
            keep_frames=request.form.get("keep_frames") == "on",
        )
    except ValueError:
        source.unlink(missing_ok=True)
        return jsonify(error="시간과 설정값에는 숫자를 입력하세요."), 400
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "status": "running", "message": "대기 중", "progress": 0}
    threading.Thread(target=process, args=(job_id, source, options), daemon=True).start()
    return jsonify(jobs[job_id]), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        return (jsonify(job), 200) if job else (jsonify(error="작업을 찾을 수 없습니다."), 404)


@app.get("/results/<path:job>/<path:filename>")
def result_file(job: str, filename: str):
    return send_from_directory(OUTPUTS / secure_filename(job), filename, as_attachment=filename.endswith((".txt", ".json")))


if __name__ == "__main__":
    app.run(host=os.environ.get("VIDEO_OCR_HOST", "127.0.0.1"), port=int(os.environ.get("VIDEO_OCR_PORT", "5000")), threaded=True)
