"""
RunPod Serverless Handler - Face Detection + Bib Number Detection
Supports GPU acceleration for both InsightFace and PaddleOCR
"""

import runpod
import base64
import cv2
import numpy as np
import requests
from concurrent.futures import ThreadPoolExecutor
from insightface.app import FaceAnalysis
from paddleocr import PaddleOCR

MAX_WORKERS = 10  # Parallel workers for batch processing

# =====================================================
# Load models on startup
# =====================================================

# GPU Diagnostics
import onnxruntime as ort
print("=== GPU Diagnostics ===")
print(f"ONNX Runtime providers: {ort.get_available_providers()}")
print(f"CUDA available: {'CUDAExecutionProvider' in ort.get_available_providers()}")

# Face detection model (InsightFace)
print("Loading InsightFace model...")
face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0)  # 0 = GPU
print("✓ InsightFace initialized with GPU (ctx_id=0)")

# Bib number detection model (PaddleOCR)
print("Loading PaddleOCR model...")
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True, show_log=False)
print("✓ PaddleOCR initialized with GPU")
print("=======================")

# =====================================================
# Utils
# =====================================================

def decode_base64_image(b64: str):
    """Decode base64 string to OpenCV image"""
    try:
        img_bytes = base64.b64decode(b64)
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def download_image(url: str):
    """Download image from URL"""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        img_array = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def detect_bib_numbers(image):
    """
    Detect bib numbers in image using PaddleOCR

    Returns:
        List[dict]: Detected bib numbers with number, confidence, and bbox
    """
    try:
        result = ocr.ocr(image, cls=True)

        if not result or not result[0]:
            return []

        bib_numbers = []
        for detection in result[0]:
            bbox, (text, confidence) = detection

            # Extract only digits (bib numbers are numeric)
            cleaned_text = ''.join(filter(str.isdigit, text))

            # Filter by:
            # 1. Has at least one digit
            # 2. Confidence > 0.5
            # 3. Reasonable length for bib number (1-5 digits)
            if cleaned_text and confidence > 0.5 and 1 <= len(cleaned_text) <= 5:
                bib_numbers.append({
                    "number": cleaned_text,
                    "confidence": float(confidence),
                    "bbox": [[int(p[0]), int(p[1])] for p in bbox]
                })

        # Sort by confidence (highest first)
        bib_numbers.sort(key=lambda x: x['confidence'], reverse=True)
        return bib_numbers

    except Exception as e:
        print(f"Error detecting bibs: {e}")
        return []


def process_single_image(item, mode="face"):
    """
    Process single image: download + face/bib detection

    Args:
        item: dict with 'id' and 'url'
        mode: 'face', 'bib', or 'both'
    """
    try:
        img = download_image(item.get("url"))
        if img is None:
            raise ValueError("Invalid image or URL")

        result = {
            "id": item.get("id"),
            "error": None
        }

        # Detect faces if requested
        if mode in ["face", "both"]:
            faces = face_app.get(img)
            result["faces_count"] = len(faces)
            result["faces"] = [
                {
                    "face_index": idx,
                    "embedding": face.embedding.tolist(),
                    "confidence": float(face.det_score)
                }
                for idx, face in enumerate(faces)
            ]

        # Detect bibs if requested
        if mode in ["bib", "both"]:
            bibs = detect_bib_numbers(img)
            result["bibs_count"] = len(bibs)
            result["bibs"] = bibs

        return result

    except Exception as e:
        error_result = {
            "id": item.get("id"),
            "error": str(e)
        }

        # Add empty arrays based on mode
        if mode in ["face", "both"]:
            error_result["faces_count"] = 0
            error_result["faces"] = []
        if mode in ["bib", "both"]:
            error_result["bibs_count"] = 0
            error_result["bibs"] = []

        return error_result


# =====================================================
# Handler
# =====================================================

def handler(event):
    """
    Main RunPod handler

    Input formats:

    1. Batch mode (URLs):
       {
         "input": {
           "images": [{"id": "1", "url": "https://..."}],
           "mode": "face" | "bib" | "both"  (optional, default: "face")
         }
       }

    2. Single mode (base64):
       {
         "input": {
           "image": "base64_string_here",
           "mode": "face" | "bib" | "both"  (optional, default: "face")
         }
       }
    """
    input_data = event.get("input", {})
    mode = input_data.get("mode", "face")  # Default: face detection only

    # Validate mode
    if mode not in ["face", "bib", "both"]:
        return {"error": f"Invalid mode '{mode}'. Use 'face', 'bib', or 'both'"}

    # ============================================
    # BATCH MODE (URLs)
    # ============================================
    if "images" in input_data:
        images = input_data["images"]

        # Process in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(
                lambda item: process_single_image(item, mode),
                images
            ))

        return {"results": results}

    # ============================================
    # SINGLE MODE (base64)
    # ============================================
    elif "image" in input_data:
        img = decode_base64_image(input_data["image"])
        if img is None:
            return {"error": "Invalid base64 image"}

        result = {"error": None}

        # Detect faces if requested
        if mode in ["face", "both"]:
            faces = face_app.get(img)
            if faces:
                result["faces_count"] = len(faces)
                result["embedding"] = faces[0].embedding.tolist()  # First face only
            else:
                result["faces_count"] = 0
                result["embedding"] = None

        # Detect bibs if requested
        if mode in ["bib", "both"]:
            bibs = detect_bib_numbers(img)
            result["bibs_count"] = len(bibs)
            result["bibs"] = bibs

        return result

    return {
        "error": "No valid input provided. Use 'image' (base64) or 'images' (batch URLs)"
    }


runpod.serverless.start({"handler": handler})
