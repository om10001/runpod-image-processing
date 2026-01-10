# API: InsightFace Embeddings (RunPod Serverless)

Base URL: `https://api.runpod.ai/v2/{ENDPOINT_ID}`

Headers requeridos:
```
Authorization: Bearer {RUNPOD_API_KEY}
Content-Type: application/json
```

---

## 1. /runsync - Imagen individual (base64)

Uso: selfies, pruebas rapidas, baja frecuencia

### Request
```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer {RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "image": "BASE64_IMAGE_STRING"
    }
  }'
```

`image` debe ser base64 puro, sin `data:image/...;base64,`

### Response - Cara detectada
```json
{
  "id": "sync-xxx",
  "status": "COMPLETED",
  "output": {
    "faces_count": 1,
    "embedding": [-0.0123, 0.8342, -1.2219, 0.0451, ...],
    "error": null
  }
}
```

`embedding` = vector facial (List[float], ~512 dimensiones)

### Response - Sin caras
```json
{
  "output": {
    "faces_count": 0,
    "embedding": null,
    "error": null
  }
}
```

---

## 2. /runsync - Batch de imagenes por URL (RECOMENDADO)

Uso: indexacion masiva, fotos grandes, produccion

### Request
```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer {RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "user_001",
          "url": "https://cdn.example.com/photos/user_001.jpg"
        },
        {
          "id": "user_002",
          "url": "https://cdn.example.com/photos/user_002.jpg"
        }
      ]
    }
  }'
```

Reglas:
- `id` = identificador libre (user_id, photo_id, etc.)
- `url` = imagen publica (S3, Cloudflare R2, GCS, CDN)

### Response - Exito
```json
{
  "id": "sync-xxx",
  "status": "COMPLETED",
  "output": {
    "results": [
      {
        "id": "user_001",
        "faces_count": 1,
        "faces": [
          {
            "face_index": 0,
            "embedding": [0.022, -0.912, 1.442, 0.331, ...],
            "confidence": 0.98
          }
        ],
        "error": null
      },
      {
        "id": "user_002",
        "faces_count": 0,
        "faces": [],
        "error": null
      }
    ]
  }
}
```

### Response - Error parcial (imagen caida)
```json
{
  "output": {
    "results": [
      {
        "id": "user_003",
        "faces_count": 0,
        "faces": [],
        "error": "404 Client Error: Not Found for url"
      }
    ]
  }
}
```

El batch NUNCA falla completo, cada imagen responde individualmente.

---

## 3. /run - Async (para jobs largos)

Si tienes muchas imagenes, usa `/run` en lugar de `/runsync`:

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/run \
  -H "Authorization: Bearer {RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [...]
    }
  }'
```

Response:
```json
{
  "id": "job-abc123",
  "status": "IN_QUEUE"
}
```

Luego consultas el estado:
```bash
curl https://api.runpod.ai/v2/{ENDPOINT_ID}/status/job-abc123 \
  -H "Authorization: Bearer {RUNPOD_API_KEY}"
```

---

## 4. /health - Estado del endpoint

```bash
curl https://api.runpod.ai/v2/{ENDPOINT_ID}/health \
  -H "Authorization: Bearer {RUNPOD_API_KEY}"
```

Response:
```json
{
  "jobs": {
    "completed": 10,
    "failed": 0,
    "inProgress": 1,
    "inQueue": 0
  },
  "workers": {
    "idle": 1,
    "ready": 1,
    "running": 0
  }
}
```

---

## Integracion con Lovable

1. Subir imagen a Object Storage (S3, R2, etc.)
2. Obtener URL publica
3. Llamar `/runsync` con `images`
4. Guardar embedding en DB
5. Comparar / buscar / clusterizar
