"""
RunPod Serverless Handler — Face Detection + Bib Number Recognition
GPU-optimized with two-phase processing: parallel I/O then sequential GPU.

Supported modes: "face" | "bib" | "both"  (default: "face")

INPUT — Batch mode:
    {
        "input": {
            "mode": "face" | "bib" | "both",         // optional, default "face"
            "images": [{"id": "foto-1", "url": "https://..."}]
        }
    }

INPUT — Single mode (base64):
    {
        "input": {
            "mode": "face" | "bib" | "both",         // optional, default "face"
            "image": "iVBORw0KGgo..."                 // pure base64, no data:image/ prefix
        }
    }

OUTPUT — Batch mode:
    {
        "results": [
            {
                "id": "foto-1",
                "faces_count": 2,
                "faces": [{"face_index": 0, "embedding": [...512 floats], "confidence": 0.98}],
                "bibs_count": 1,
                "bibs": [{"number": "1234", "confidence": 0.91, "bbox": [[x,y], ...]}],
                "error": null
            }
        ]
    }
    Notes:
    - faces/faces_count only present when mode includes "face"
    - bibs/bibs_count only present when mode includes "bib"
    - Per-item error does NOT cancel the batch

OUTPUT — Single mode:
    {
        "faces_count": 1,
        "embedding": [...512 floats],   // first face only; null if no face detected
        "bibs_count": 1,
        "bibs": [{"number": "1234", "confidence": 0.91, "bbox": [[x,y], ...]}],
        "error": null
    }

OUTPUT — Request errors:
    {"error": "Invalid mode 'foo'. Use 'face', 'bib', or 'both'"}
    {"error": "Batch too large: 600 > max 500"}
    {"error": "No valid input. Use 'image' (base64) or 'images' (batch URLs)"}
    {"error": "Invalid base64 image"}
"""

from __future__ import annotations

import base64
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
import requests
import runpod
from insightface.app import FaceAnalysis
from paddleocr import PaddleOCR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

VALID_MODES = ("face", "bib", "both")


# =============================================================================
# Configuration
# =============================================================================

@dataclass(frozen=True)
class Config:
    """
    Application configuration loaded from environment variables.

    Env var           Default   Description
    ────────────────────────────────────────────────────────────────
    MAX_DOWNLOAD_WORKERS  30    Thread pool size for parallel image downloads
    MAX_BATCH_SIZE       500    Hard cap on images per request
    REQUEST_TIMEOUT       15    HTTP download timeout in seconds
    GPU_CTX                0    CUDA device index (0=GPU, -1=CPU fallback)
    FACE_MODEL      buffalo_l   InsightFace model name
    MIN_BIB_CONFIDENCE  0.5     Minimum OCR confidence to accept a bib detection
    MAX_BIB_DIGITS        5     Maximum digits accepted as a valid bib number
    """
    max_download_workers: int
    max_batch_size: int
    request_timeout: int
    gpu_ctx: int
    face_model: str
    min_bib_confidence: float
    max_bib_digits: int

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            max_download_workers=int(os.getenv("MAX_DOWNLOAD_WORKERS", "30")),
            max_batch_size=int(os.getenv("MAX_BATCH_SIZE", "500")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "15")),
            gpu_ctx=int(os.getenv("GPU_CTX", "0")),
            face_model=os.getenv("FACE_MODEL", "buffalo_l"),
            min_bib_confidence=float(os.getenv("MIN_BIB_CONFIDENCE", "0.5")),
            max_bib_digits=int(os.getenv("MAX_BIB_DIGITS", "5")),
        )


# =============================================================================
# Data Transfer Objects
# =============================================================================

@dataclass
class FaceData:
    face_index: int
    embedding: list[float]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_index": self.face_index,
            "embedding": self.embedding,
            "confidence": self.confidence,
        }


@dataclass
class BibData:
    number: str
    confidence: float
    bbox: list[list[int]]  # 4 points [[x,y], [x,y], [x,y], [x,y]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }


@dataclass
class ImageResult:
    id: str
    faces_count: int = 0
    faces: list[FaceData] = field(default_factory=list)
    bibs_count: int = 0
    bibs: list[BibData] = field(default_factory=list)
    error: str | None = None

    def to_dict_by_mode(self, mode: str) -> dict[str, Any]:
        """
        Builds a per-item response matching the requested detection mode.

        For batch requests, clients expect fields for the requested mode only.
        """
        result: dict[str, Any] = {"id": self.id, "error": self.error}

        if mode in ("face", "both"):
            result["faces_count"] = self.faces_count
            result["faces"] = [f.to_dict() for f in self.faces]

        if mode in ("bib", "both"):
            result["bibs_count"] = self.bibs_count
            result["bibs"] = [b.to_dict() for b in self.bibs]

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "faces_count": self.faces_count,
            "faces": [f.to_dict() for f in self.faces],
            "bibs_count": self.bibs_count,
            "bibs": [b.to_dict() for b in self.bibs],
            "error": self.error,
        }


# =============================================================================
# Image Loader
# =============================================================================

class ImageLoader:
    """Loads images from URLs or base64 strings into numpy arrays."""

    def __init__(self, config: Config) -> None:
        self._timeout = config.request_timeout

    # Hard cap on response size — prevents a thread from holding memory
    # if a URL accidentally points to a video or other large file.
    _MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB

    def from_url(self, url: str) -> np.ndarray | None:
        """
        Download and decode image from URL.
        Returns None on any failure — never raises.

        Timeout is a (connect, read) tuple:
          - connect: seconds to establish TCP connection
          - read: seconds between data chunks (not total transfer time)
        Response is capped at _MAX_IMAGE_BYTES to prevent memory exhaustion
        from unexpectedly large files (videos, etc.).
        """
        try:
            resp = requests.get(url, timeout=(5, self._timeout))
            resp.raise_for_status()

            if len(resp.content) > self._MAX_IMAGE_BYTES:
                logger.warning(
                    "Skipping oversized response (%d bytes) for url=%s",
                    len(resp.content), url,
                )
                return None

            arr = np.frombuffer(resp.content, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("cv2.imdecode returned None for url=%s", url)
            return img
        except Exception as exc:
            logger.warning("Download failed url=%s: %s", url, exc)
            return None

    def from_base64(self, b64: str) -> np.ndarray | None:
        """
        Decode image from pure base64 string (no data:image/ prefix).
        Returns None on any failure — never raises.
        """
        try:
            img_bytes = base64.b64decode(b64)
            arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("cv2.imdecode returned None for base64 input")
            return img
        except Exception as exc:
            logger.warning("Base64 decode failed: %s", exc)
            return None


# =============================================================================
# Face Detector
# =============================================================================

class FaceDetector:
    """Detects faces and returns 512-dim embeddings using InsightFace buffalo_l."""

    def __init__(self, config: Config) -> None:
        logger.info("Loading InsightFace model=%s ctx_id=%d ...", config.face_model, config.gpu_ctx)
        self._app = FaceAnalysis(name=config.face_model)
        self._app.prepare(ctx_id=config.gpu_ctx)
        logger.info("InsightFace ready")

    def process(self, image: np.ndarray) -> list[FaceData]:
        """
        Detect all faces in image.
        Returns list of FaceData sorted by detection score (highest first).
        Returns [] if no faces found. Never raises.
        """
        try:
            faces = self._app.get(image)
            results = [
                FaceData(
                    face_index=idx,
                    embedding=face.embedding.tolist(),
                    confidence=float(face.det_score),
                )
                for idx, face in enumerate(faces)
            ]
            results.sort(key=lambda f: f.confidence, reverse=True)
            return results
        except Exception as exc:
            logger.error("FaceDetector.process failed: %s", exc)
            return []


# =============================================================================
# Bib Detector
# =============================================================================

class BibDetector:
    """
    Detects race bib numbers using PaddleOCR.
    Filters to numeric-only text with 1–MAX_BIB_DIGITS digits and
    confidence >= MIN_BIB_CONFIDENCE.
    """

    def __init__(self, config: Config) -> None:
        self._min_confidence = config.min_bib_confidence
        self._max_digits = config.max_bib_digits
        logger.info("Loading PaddleOCR gpu=%s ...", config.gpu_ctx >= 0)
        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            use_gpu=(config.gpu_ctx >= 0),
            show_log=False,
        )
        logger.info("PaddleOCR ready")

    def process(self, image: np.ndarray) -> list[BibData]:
        """
        Detect bib numbers in image.
        Returns list sorted by confidence (highest first).
        Returns [] if none found or on error. Never raises.
        """
        try:
            raw = self._ocr.ocr(image, cls=True)
            if not raw or not raw[0]:
                return []

            bibs: list[BibData] = []
            for detection in raw[0]:
                bbox, (text, confidence) = detection
                digits = "".join(filter(str.isdigit, text))
                if (
                    digits
                    and confidence >= self._min_confidence
                    and 1 <= len(digits) <= self._max_digits
                ):
                    bibs.append(BibData(
                        number=digits,
                        confidence=float(confidence),
                        bbox=[[int(p[0]), int(p[1])] for p in bbox],
                    ))

            bibs.sort(key=lambda b: b.confidence, reverse=True)
            return bibs

        except Exception as exc:
            logger.error("BibDetector.process failed: %s", exc)
            return []


# =============================================================================
# Batch Processor — two-phase GPU architecture
# =============================================================================

class BatchProcessor:
    """
    Processes a list of {id, url} items in two strict phases:

    Phase 1 — Parallel download (I/O bound, GPU idle):
        All images downloaded concurrently via ThreadPoolExecutor.
        Thread count = MAX_DOWNLOAD_WORKERS (default 30).
        Each thread has a bounded lifetime: HTTP timeout = REQUEST_TIMEOUT.
        Failures return (item, None) — never propagate to the pool.

    Phase 2 — Sequential GPU inference (GPU bound, no CUDA contention):
        Linear for-loop over downloaded images.
        Each image wrapped in try/except — one failure never blocks others.
        GPU runs at maximum utilization with zero context-switching overhead.
    """

    def __init__(
        self,
        config: Config,
        loader: ImageLoader,
        face_detector: FaceDetector,
        bib_detector: BibDetector,
    ) -> None:
        self._config = config
        self._loader = loader
        self._face_detector = face_detector
        self._bib_detector = bib_detector

    def process(self, items: list[dict], mode: str) -> list[dict]:
        # Phase 1: Download all images in parallel (pure I/O)
        # executor.map() over a finite list — guaranteed to terminate because:
        # - each download has a hard HTTP timeout (REQUEST_TIMEOUT seconds)
        # - _download_item never raises, always returns a tuple
        with ThreadPoolExecutor(max_workers=self._config.max_download_workers) as ex:
            downloaded = list(ex.map(self._download_item, items))

        # Phase 2: GPU inference — sequential, bounded, isolated per image
        results = []
        for item, img in downloaded:
            try:
                results.append(self._process_gpu(item, img, mode))
            except Exception as exc:
                logger.error("GPU processing failed id=%s: %s", item.get("id"), exc)
                results.append(
                    ImageResult(id=item.get("id"), error=str(exc)).to_dict_by_mode(mode)
                )

        return results

    def _download_item(self, item: dict) -> tuple[dict, np.ndarray | None]:
        """Always returns (item, img_or_None). Never raises."""
        img = self._loader.from_url(item.get("url", ""))
        return item, img

    def _process_gpu(self, item: dict, img: np.ndarray | None, mode: str) -> dict:
        if img is None:
            return ImageResult(id=item.get("id"), error="Failed to download image").to_dict_by_mode(mode)

        result = ImageResult(id=item.get("id"))
        if mode in ("face", "both"):
            result.faces = self._face_detector.process(img)
            result.faces_count = len(result.faces)
        if mode in ("bib", "both"):
            result.bibs = self._bib_detector.process(img)
            result.bibs_count = len(result.bibs)
        return result.to_dict_by_mode(mode)


# =============================================================================
# Request Handler
# =============================================================================

class RequestHandler:
    """Routes incoming RunPod events to the appropriate processing path."""

    def __init__(
        self,
        config: Config,
        loader: ImageLoader,
        face_detector: FaceDetector,
        bib_detector: BibDetector,
        batch_processor: BatchProcessor,
    ) -> None:
        self._config = config
        self._loader = loader
        self._face_detector = face_detector
        self._bib_detector = bib_detector
        self._batch = batch_processor

    def handle(self, event: dict) -> dict:
        input_data = event.get("input", {})
        mode = input_data.get("mode", "face")

        if mode not in VALID_MODES:
            return {"error": f"Invalid mode '{mode}'. Use 'face', 'bib', or 'both'"}

        if "images" in input_data:
            return self._handle_batch(input_data["images"], mode)

        if "image" in input_data:
            return self._handle_single(input_data["image"], mode)

        return {"error": "No valid input. Use 'image' (base64) or 'images' (batch URLs)"}

    def _handle_batch(self, images: list, mode: str) -> dict:
        if not isinstance(images, list):
            return {"error": "'images' must be a list"}

        if len(images) > self._config.max_batch_size:
            return {"error": f"Batch too large: {len(images)} > max {self._config.max_batch_size}"}

        if len(images) == 0:
            return {"results": []}

        logger.info("Batch request: %d images, mode=%s", len(images), mode)
        results = self._batch.process(images, mode)
        logger.info("Batch complete: %d results", len(results))
        return {"results": results}

    def _handle_single(self, b64_image: str, mode: str) -> dict:
        img = self._loader.from_base64(b64_image)
        if img is None:
            return {"error": "Invalid base64 image"}

        result: dict[str, Any] = {"error": None}

        if mode in ("face", "both"):
            faces = self._face_detector.process(img)
            result["faces_count"] = len(faces)
            # Keep flat `embedding` field for backwards compatibility with existing clients
            result["embedding"] = faces[0].embedding if faces else None

        if mode in ("bib", "both"):
            bibs = self._bib_detector.process(img)
            result["bibs_count"] = len(bibs)
            result["bibs"] = [b.to_dict() for b in bibs]

        return result


# =============================================================================
# Application Bootstrap
# =============================================================================

class Application:
    """Wires all components together and starts the RunPod serverless loop."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.from_env()
        self._log_gpu_diagnostics()

        loader = ImageLoader(self.config)
        face_detector = FaceDetector(self.config)
        bib_detector = BibDetector(self.config)
        batch_processor = BatchProcessor(self.config, loader, face_detector, bib_detector)

        self.handler = RequestHandler(
            self.config, loader, face_detector, bib_detector, batch_processor
        )

    def _log_gpu_diagnostics(self) -> None:
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            cuda_ok = "CUDAExecutionProvider" in providers
            logger.info("ONNX providers: %s", providers)
            logger.info("CUDA available: %s", cuda_ok)
            if not cuda_ok:
                logger.warning("CUDA not available — inference will fall back to CPU (slow)")
        except Exception as exc:
            logger.warning("GPU diagnostics failed: %s", exc)

    def run(self) -> None:
        logger.info(
            "Starting RunPod handler | max_download_workers=%d max_batch_size=%d gpu_ctx=%d",
            self.config.max_download_workers,
            self.config.max_batch_size,
            self.config.gpu_ctx,
        )
        runpod.serverless.start({"handler": self.handler.handle})


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    Application().run()
