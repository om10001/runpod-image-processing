📌 API: InsightFace Embeddings
1️⃣ /index – Imagen única (base64)

👉 Uso: selfies, pruebas rápidas, baja frecuencia
👉 NO recomendado para HQ masivo

🔹 Request

POST /index
Content-Type: application/json

{
  "image": "BASE64_IMAGE_STRING"
}


image debe ser base64 puro, sin data:image/...;base64,

🔹 Response — Cara detectada
{
  "faces_count": 1,
  "embedding": [
    -0.0123,
    0.8342,
    -1.2219,
    0.0451
  ],
  "error": null
}


📌 embedding → vector facial (List[float], ~512 dimensiones)

🔹 Response — Sin caras
{
  "faces_count": 0,
  "embedding": null,
  "error": null
}

🔹 Response — Error (imagen inválida)
{
  "detail": "Invalid base64 image"
}

🔹 curl example
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{
    "image": "iVBORw0KGgoAAAANSUhEUgAA..."
  }'

2️⃣ /index-batch – Batch de imágenes HQ (RECOMENDADO)

👉 Uso: indexación masiva, fotos grandes, producción
👉 Método correcto para Lovable

🔹 Request

POST /index-batch
Content-Type: application/json

{
  "mode": "batch",
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


📌 Reglas importantes para Lovable

id → identificador libre (user_id, photo_id, etc.)

url → imagen pública (S3, Cloudflare R2, GCS, CDN)

RunPod descarga la imagen

🔹 Response — Éxito
{
  "results": [
    {
      "id": "user_001",
      "faces_count": 1,
      "faces": [
        {
          "face_index": 0,
          "embedding": [
            0.022,
            -0.912,
            1.442,
            0.331
          ],
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

🔹 Response — Error parcial (imagen caída)
{
  "results": [
    {
      "id": "user_003",
      "faces_count": 0,
      "faces": [],
      "error": "404 Client Error: Not Found for url"
    }
  ]
}


📌 Importante:
El batch NUNCA falla completo, cada imagen responde individualmente.

🔹 curl example (HQ real)
curl -X POST http://localhost:8000/index-batch \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "batch",
    "images": [
      {
        "id": "img_001",
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/37/Dagestani_man.jpg"
      }
    ]
  }'

🧠 Cómo debe pensarlo Lovable (IMPORTANTÍSIMO)
Integración correcta
1. Subir imagen → Object Storage
2. Obtener URL pública
3. Llamar /index-batch
4. Guardar embedding
5. Comparar / buscar / clusterizar