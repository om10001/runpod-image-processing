import runpod
import base64
import cv2
import numpy as np
import requests
from insightface.app import FaceAnalysis

# =====================================================
# Load model on startup
# =====================================================

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0)  # 0 = GPU

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
# Handler
# =====================================================

def handler(event):
    input_data = event.get("input", {})

    # Modo batch (URLs) - /index-batch
    if "images" in input_data:
        results = []

        for item in input_data["images"]:
            try:
                img = download_image(item.get("url"))
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
                    "id": item.get("id"),
                    "faces_count": len(faces),
                    "faces": faces_data,
                    "error": None
                })

            except Exception as e:
                results.append({
                    "id": item.get("id"),
                    "faces_count": 0,
                    "faces": [],
                    "error": str(e)
                })

        return {"results": results}

    # Modo single (base64) - /index
    elif "image" in input_data:
        img = decode_base64_image(input_data["image"])
        if img is None:
            return {"error": "Invalid base64 image", "faces_count": 0, "embedding": None}

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

    return {"error": "No valid input provided. Use 'image' (base64) or 'images' (batch URLs)"}


runpod.serverless.start({"handler": handler})
