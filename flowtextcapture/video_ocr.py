"""Cross-platform video-to-text pipeline.

The module deliberately keeps the processing engine independent from any GUI so it
can be used from the command line, desktop browsers, and phones on the same LAN.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np
from skimage.metrics import structural_similarity

Progress = Callable[[str, float], None]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}


@dataclass
class PipelineOptions:
    start: float = 0.0
    end: float | None = None
    sample_interval: float = 0.0
    similarity: float = 0.98
    language: str = "ko,en"
    ocr_engine: str = "auto"
    spellcheck: bool = True
    keep_frames: bool = True


@dataclass
class TextBlock:
    frame: str
    timestamp: float
    text: str
    corrected_text: str
    crop: str


def _noop(_message: str, _fraction: float) -> None:
    pass


def _safe_name(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._")
    return value or "video"


def _iter_images(folder: Path) -> Iterable[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


class TextRegionDetector:
    """Find likely text groups from image structure, without hard-coded colors."""

    def detect(self, image: np.ndarray) -> tuple[int, int, int, int]:
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        panel = self._detect_panel(gray)
        if panel is not None:
            return panel

        # Generic fallback for subtitles or images without a distinct panel.
        # Text has strong, closely spaced horizontal gradients under either theme.
        grad = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad = cv2.convertScaleAbs(grad)
        _, mask = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kw = max(9, width // 45)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, kw), np.uint8))
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: list[tuple[int, int, int, int, float]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area_ratio = (w * h) / float(width * height)
            aspect = w / max(h, 1)
            if w >= width * 0.06 and h >= max(8, height * 0.012) and aspect > 1.2 and area_ratio < 0.65:
                cx, cy = x + w / 2, y + h / 2
                centrality = 1.0 - min(1.0, abs(cx - width / 2) / (width / 2))
                density = cv2.countNonZero(mask[y : y + h, x : x + w]) / max(w * h, 1)
                boxes.append((x, y, w, h, centrality * 0.5 + density * 0.5))

        if not boxes:
            # A conservative center fallback preserves data when detection is unsure.
            return (int(width * 0.08), int(height * 0.12), int(width * 0.84), int(height * 0.76))

        boxes.sort(key=lambda item: item[4], reverse=True)
        anchor = boxes[0]
        ax, ay, aw, ah, _ = anchor
        pad_x, pad_y = width * 0.04, height * 0.035
        related = []
        for box in boxes:
            x, y, w, h, score = box
            horizontal_overlap = max(0, min(ax + aw, x + w) - max(ax, x))
            near = abs((x + w / 2) - (ax + aw / 2)) < width * 0.35
            if score > 0.2 and (horizontal_overlap > 0 or near) and y < ay + ah + height * 0.35 and y + h > ay - height * 0.35:
                related.append(box)
        x1 = max(0, int(min(b[0] for b in related) - pad_x))
        y1 = max(0, int(min(b[1] for b in related) - pad_y))
        x2 = min(width, int(max(b[0] + b[2] for b in related) + pad_x))
        y2 = min(height, int(max(b[1] + b[3] for b in related) + pad_y))
        return x1, y1, x2 - x1, y2 - y1

    def _detect_panel(self, gray: np.ndarray) -> tuple[int, int, int, int] | None:
        """Detect a large, uniform text card from the image's own color modes.

        This generalizes the old 4crop.py behavior: instead of fixing the card
        color to BGR 25..55, it discovers dominant luminance levels per frame.
        """
        height, width = gray.shape
        histogram = np.bincount(gray.ravel(), minlength=256).copy()
        peaks: list[int] = []
        # UI cards are normally low/mid luminance; exclude near-white text.
        for _ in range(8):
            level = int(np.argmax(histogram[:200]))
            peaks.append(level)
            histogram[max(0, level - 3) : min(256, level + 4)] = 0

        candidates: list[tuple[float, tuple[int, int, int, int]]] = []
        kernel = np.ones((13, max(15, width // 60)), np.uint8)
        for level in peaks:
            mask = cv2.inRange(gray, max(0, level - 6), min(199, level + 6))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                wr, hr = w / width, h / height
                center = (x + w / 2) / width
                if not (0.35 <= wr <= 0.90 and 0.12 <= hr <= 0.82 and 0.20 <= center <= 0.80):
                    continue
                area = wr * hr
                # Prefer the largest central reading panel, not browser chrome
                # or the short input bar usually located at the bottom.
                score = area + hr * 0.30 - abs(center - 0.5) * 0.30
                if y / height > 0.70:
                    score -= 0.15
                candidates.append((score, (x, y, w, h)))
        if not candidates:
            return None
        _, (x, y, w, h) = max(candidates, key=lambda item: item[0])
        margin = max(3, round(min(width, height) * 0.004))
        x1, y1 = max(0, x - margin), max(0, y - margin)
        x2, y2 = min(width, x + w + margin), min(height, y + h + margin)
        return x1, y1, x2 - x1, y2 - y1

    def crop(self, image: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
        x, y, w, h = self.detect(image)
        return image[y : y + h, x : x + w].copy(), (x, y, w, h)


class OCRBackend:
    name = "unknown"

    def recognize(self, image_path: Path) -> list[str]:
        raise NotImplementedError


class AppleVisionOCR(OCRBackend):
    name = "Apple Vision (accurate)"

    def __init__(self, languages: list[str]):
        from ocrmac import ocrmac

        self.ocrmac = ocrmac
        codes = {"ko": "ko-KR", "ko-KR": "ko-KR", "en": "en-US", "en-US": "en-US"}
        self.languages = list(dict.fromkeys(codes.get(language, language) for language in languages))

    def recognize(self, image_path: Path) -> list[str]:
        # VNRecognizeTextRequest is synchronous and therefore reliable inside
        # Flask's worker thread. VKC Live Text uses the current CFRunLoop and
        # can silently return [] when invoked from that background thread.
        try:
            result = self.ocrmac.OCR(
                str(image_path),
                framework="vision",
                recognition_level="accurate",
                language_preference=self.languages,
                detail=False,
            ).recognize()
        except ValueError:
            # Permit custom/older macOS language installations to auto-detect.
            result = self.ocrmac.OCR(
                str(image_path), framework="vision", recognition_level="accurate", detail=False
            ).recognize()
        return [str(item).strip() for item in result if item and str(item).strip()]


class TesseractOCR(OCRBackend):
    name = "Tesseract"

    def __init__(self, languages: list[str]):
        import pytesseract

        self.pytesseract = pytesseract
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        bundled = bundle_root / "tesseract" / ("tesseract.exe" if platform.system() == "Windows" else "tesseract")
        if bundled.is_file():
            self.pytesseract.pytesseract.tesseract_cmd = str(bundled)
            tessdata = bundled.parent / "tessdata"
            if tessdata.is_dir():
                self.config = f'--tessdata-dir "{tessdata}"'
            else:
                self.config = ""
        else:
            self.config = ""
        # Fail during selection, not halfway through a long video job.
        self.pytesseract.get_tesseract_version()
        codes = {"ko": "kor", "ko-KR": "kor", "en": "eng", "en-US": "eng"}
        self.language = "+".join(codes.get(language, language) for language in languages)

    def recognize(self, image_path: Path) -> list[str]:
        text = self.pytesseract.image_to_string(str(image_path), lang=self.language, config=self.config)
        return [line.strip() for line in text.splitlines() if line.strip()]


def make_ocr(engine: str, languages: str) -> OCRBackend:
    langs = [x.strip() for x in languages.split(",") if x.strip()]
    errors = []
    candidates = []
    if engine in {"auto", "apple"} and platform.system() == "Darwin":
        candidates.append(AppleVisionOCR)
    if engine in {"auto", "tesseract"}:
        candidates.append(TesseractOCR)
    for backend in candidates:
        try:
            return backend(langs)
        except Exception as exc:
            errors.append(f"{backend.__name__}: {exc}")
    raise RuntimeError("사용 가능한 OCR 엔진이 없습니다. " + " | ".join(errors))


class SpellChecker:
    name = "basic normalization"

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.tool = None
        if enabled:
            try:
                import language_tool_python

                self.tool = language_tool_python.LanguageTool("ko-KR")
                self.name = "LanguageTool (ko-KR)"
            except Exception:
                pass

    def correct(self, text: str) -> str:
        clean = re.sub(r"[ \t]+", " ", text).strip()
        clean = re.sub(r" *\n *", "\n", clean)
        if self.enabled and self.tool and clean:
            try:
                return self.tool.correct(clean)
            except Exception:
                return clean
        return clean


class VideoOCRPipeline:
    def __init__(self, options: PipelineOptions | None = None):
        self.options = options or PipelineOptions()
        self.detector = TextRegionDetector()

    def _extract(self, video: Path, frame_dir: Path, progress: Progress) -> list[tuple[Path, float]]:
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            raise ValueError(f"영상을 열 수 없습니다: {video}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        duration = (cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps) if fps else 0
        start = max(0.0, self.options.start)
        end = min(duration, self.options.end) if self.options.end is not None else duration
        if end <= start:
            cap.release()
            raise ValueError("종료 시간은 시작 시간보다 커야 합니다.")
        start_frame = max(0, int(round(start * fps)))
        end_frame = min(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), int(np.ceil(end * fps)))
        stride = 1 if self.options.sample_interval <= 0 else max(1, int(round(self.options.sample_interval * fps)))
        expected = max(1, int(np.ceil((end_frame - start_frame) / stride)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        saved: list[tuple[Path, float]] = []
        source_index = start_frame
        while source_index < end_frame:
            ok, frame = cap.read()
            if not ok:
                break
            relative = source_index - start_frame
            if relative % stride == 0:
                timestamp = source_index / fps
                path = frame_dir / f"frame_{source_index:06d}_{timestamp:010.3f}.jpg"
                cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 96])
                saved.append((path, timestamp))
                progress(
                    f"프레임 추출 {len(saved)}/{expected}",
                    0.05 + 0.25 * min(1.0, len(saved) / expected),
                )
            source_index += 1
        cap.release()
        return saved

    def run(self, video_path: str | Path, output_root: str | Path, progress: Progress = _noop) -> Path:
        video = Path(video_path).resolve()
        if not video.is_file():
            raise FileNotFoundError(video)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        job = Path(output_root).resolve() / f"{_safe_name(video.name)}-{stamp}"
        suffix = 1
        while job.exists():
            job = job.with_name(f"{_safe_name(video.name)}-{stamp}-{suffix}")
            suffix += 1
        frame_dir, crop_dir = job / "frames", job / "text_regions"
        frame_dir.mkdir(parents=True)
        crop_dir.mkdir()
        (job / "settings.json").write_text(json.dumps(asdict(self.options), ensure_ascii=False, indent=2), encoding="utf-8")

        progress("영상을 여는 중", 0.02)
        frames = self._extract(video, frame_dir, progress)
        if not frames:
            raise RuntimeError("추출된 프레임이 없습니다.")

        selected: list[tuple[Path, float]] = []
        previous = None
        for index, (frame_path, timestamp) in enumerate(frames):
            image = cv2.imread(str(frame_path))
            crop, _ = self.detector.crop(image)
            normalized = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (480, 240))
            score = structural_similarity(previous, normalized) if previous is not None else 0.0
            if previous is None or score < self.options.similarity:
                crop_path = crop_dir / f"text_{index:06d}_{timestamp:010.3f}.png"
                cv2.imwrite(str(crop_path), crop)
                selected.append((crop_path, timestamp))
                previous = normalized
            progress(f"텍스트 영역 분석 {index + 1}/{len(frames)}", 0.30 + 0.25 * (index + 1) / len(frames))

        ocr = make_ocr(self.options.ocr_engine, self.options.language)
        checker = SpellChecker(self.options.spellcheck)
        blocks = []
        for index, (crop_path, timestamp) in enumerate(selected):
            raw = "\n".join(ocr.recognize(crop_path))
            corrected = checker.correct(raw)
            blocks.append(TextBlock(crop_path.name, timestamp, raw, corrected, str(crop_path.relative_to(job))))
            progress(f"OCR {index + 1}/{len(selected)} · {ocr.name}", 0.55 + 0.43 * (index + 1) / max(len(selected), 1))

        def render(field: str) -> str:
            parts = []
            last = None
            for block in blocks:
                value = getattr(block, field).strip()
                if value and value != last:
                    parts.append(f"[{block.timestamp:0.2f}s]\n{value}")
                    last = value
            return "\n\n".join(parts) + ("\n" if parts else "")

        (job / "extracted.txt").write_text(render("text"), encoding="utf-8")
        (job / "corrected.txt").write_text(render("corrected_text"), encoding="utf-8")
        manifest = {"video": video.name, "ocr_engine": ocr.name, "spellchecker": checker.name, "blocks": [asdict(x) for x in blocks]}
        (job / "results.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if not any(block.text.strip() for block in blocks):
            raise RuntimeError(
                "텍스트 영역은 찾았지만 OCR 결과가 비어 있습니다. "
                "언어 설정과 OCR 엔진 설치 상태를 확인하세요."
            )
        if not self.options.keep_frames:
            shutil.rmtree(frame_dir)
        progress("완료", 1.0)
        return job


def main() -> None:
    parser = argparse.ArgumentParser(description="동영상 중앙의 텍스트를 자동 추출합니다.")
    parser.add_argument("video")
    parser.add_argument("-o", "--output", default="outputs")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--end", type=float)
    parser.add_argument("--interval", type=float, default=0.0, help="0이면 모든 프레임")
    parser.add_argument("--similarity", type=float, default=0.98)
    parser.add_argument("--engine", choices=["auto", "apple", "tesseract"], default="auto")
    parser.add_argument("--no-spellcheck", action="store_true")
    args = parser.parse_args()
    options = PipelineOptions(args.start, args.end, args.interval, args.similarity, ocr_engine=args.engine, spellcheck=not args.no_spellcheck)
    result = VideoOCRPipeline(options).run(args.video, args.output, lambda m, p: print(f"{p:>6.1%} {m}"))
    print(result)


if __name__ == "__main__":
    main()
