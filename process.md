📘 InsightFace RunPod – Image Processing API

Servicio serverless en RunPod para detección facial y generación de embeddings usando InsightFace (buffalo_l).

🔐 Autenticación

El endpoint se consume vía RunPod API.

Header requerido:

Authorization: Bearer <RUNPOD_API_KEY>
Content-Type: application/json

🌐 Endpoint Base
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync


Todas las solicitudes se envían en el body bajo la clave input.

🧠 Modelo

Modelo: InsightFace buffalo_l

Dimensión del embedding: 512

Métrica recomendada: Cosine

Selección de rostro: mayor confidence (det_score)

📦 Endpoint 1 — Procesar imagen individual (Base64)

Genera el embedding de la mejor cara detectada en una imagen.

📥 Request
{
  "input": {
    "image": "BASE64_ENCODED_IMAGE"
  }
}

📤 Response — Cara detectada
{
  "faces_count": 1,
  "embedding": [
    0.0123,
    -0.4567,
    ...
  ],
  "confidence": 0.98,
  "error": null
}

📤 Response — Sin caras
{
  "faces_count": 0,
  "embedding": null,
  "error": null
}

📤 Response — Error
{
  "error": "Invalid image"
}

📦 Endpoint 2 — Procesamiento por lotes (URLs)

Procesa múltiples imágenes remotas y devuelve todas las caras detectadas por imagen.

📥 Request
{
  "input": {
    "mode": "batch",
    "images": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg"
    ]
  }
}


🔒 Límite: máximo 10 imágenes por request.

📤 Response — Batch exitoso
{
  "results": [
    {
      "file": "https://example.com/image1.jpg",
      "faces": [
        {
          "embedding": [
            0.0123,
            -0.4567,
            ...
          ],
          "confidence": 0.97,
          "face_index": 0,
          "bbox": [120, 45, 260, 210]
        }
      ],
      "faces_count": 1,
      "error": null
    }
  ]
}

📤 Response — Imagen con error
{
  "results": [
    {
      "file": "https://example.com/broken.jpg",
      "faces": [],
      "faces_count": 0,
      "error": "404 Client Error"
    }
  ]
}

📦 Endpoint 3 — Búsqueda facial (selfie)

⚠️ Es el mismo endpoint que imagen individual.
La diferencia es cómo se usa el embedding downstream (matching).

📥 Request
{
  "input": {
    "image": "BASE64_ENCODED_SELFIE"
  }
}

📤 Response
{
  "faces_count": 1,
  "embedding": [
    0.0312,
    -0.8123,
    ...
  ],
  "confidence": 0.99,
  "error": null
}

🚫 Casos inválidos
Request inválido
{
  "input": {
    "foo": "bar"
  }
}

Response
{
  "error": "Invalid input format"
}

📏 Límites y restricciones
Regla	Valor
Imágenes por batch	10
Embedding size	512
Timeout URL	30s
Formatos soportados	JPG, PNG
GPU	Automático (si disponible)
🧠 Buenas prácticas

Normalizar embeddings antes de guardar en DB

Usar Cosine similarity

Rechazar embeddings con confidence < 0.5

Guardar bbox y confidence como metadata

No mezclar embeddings de otros modelos

🧩 Ejemplo cURL
Imagen individual
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "image": "BASE64_IMAGE"
    }
  }'

Batch
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "mode": "batch",
      "images": [
        "https://example.com/a.jpg",
        "https://example.com/b.jpg"
      ]
    }
  }'

🧠 Estado del servicio

✅ Producción-ready

✅ Serverless

✅ GPU-aware

✅ Determinístico

✅ Compatible con Qdrant / pgvector