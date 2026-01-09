from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import base64
import cv2
import numpy as np
import requests

from insightface.app import FaceAnalysis

# =====================================================
# App
# =====================================================

app = FastAPI(
    title="InsightFace API",
    version="1.0",
    description="Face indexing service using InsightFace"
)

# =====================================================
# Load model on startup
# =====================================================

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=-1)  # -1 = CPU | 0 = GPU

# =====================================================
# Schemas (DTOs)
# =====================================================

class SingleImageRequest(BaseModel):
    image: str  # base64 image


class BatchImageItem(BaseModel):
    id: str     # client-side identifier
    url: str    # public image URL


class BatchImageRequest(BaseModel):
    mode: str = "batch"
    images: List[BatchImageItem]

# =====================================================
# Utils
# =====================================================

def decode_base64_image(b64: str):
    try:
        img_bytes = base64.b64decode(b64)
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def download_image(url: str):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        img_array = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None

# =====================================================
# Endpoints
# =====================================================

@app.post("/index")
def index_face(payload: SingleImageRequest):
    """
    Index a single image (selfie).
    Returns the embedding of the first detected face.
    """
    img = decode_base64_image(payload.image)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    faces = face_app.get(img)

    if not faces:
        return {
            "faces_count": 0,
            "embedding": None,
            "error": None
        }

    return {
        "faces_count": len(faces),
        "embedding": faces[0].embedding.tolist(),
        "error": None
    }


@app.post("/index-batch")
def index_faces_batch(payload: BatchImageRequest):
    """
    Index multiple images using URLs.
    Each image is identified by a client-provided `id`.
    """
    if payload.mode != "batch":
        raise HTTPException(status_code=400, detail="mode must be 'batch'")

    results = []

    for item in payload.images:
        try:
            img = download_image(item.url)
            if img is None:
                raise ValueError("Invalid image or URL")

            faces = face_app.get(img)

            faces_data = [
                {
                    "face_index": idx,
                    "embedding": face.embedding.tolist(),
                    "confidence": float(face.det_score)
                }
                for idx, face in enumerate(faces)
            ]

            results.append({
                "id": item.id,
                "faces_count": len(faces),
                "faces": faces_data,
                "error": None
            })

        except Exception as e:
            results.append({
                "id": item.id,
                "faces_count": 0,
                "faces": [],
                "error": str(e)
            })

    return {"results": results}
