# Solución Alternativa: Deployment sin Docker Hub

## Problema
El push a Docker Hub está fallando con error "400 Bad request" en capas específicas. Esto es un problema conocido con imágenes grandes (>8GB) o conexiones inestables desde WSL2.

## Solución 1: Push desde servidor remoto (RECOMENDADO)

### Opción A: Usar GitHub Actions (GRATIS)

1. **Commit y push el código a GitHub:**
   ```bash
   git add app.py Dockerfile requirements.txt
   git commit -m "Add GPU diagnostics for RunPod deployment"
   git push origin main
   ```

2. **Crear `.github/workflows/docker-push.yml`:**
   ```yaml
   name: Build and Push Docker Image

   on:
     push:
       branches: [ main ]
     workflow_dispatch:

   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3

         - name: Login to Docker Hub
           uses: docker/login-action@v2
           with:
             username: ${{ secrets.DOCKERHUB_USERNAME }}
             password: ${{ secrets.DOCKERHUB_TOKEN }}

         - name: Build and push
           uses: docker/build-push-action@v4
           with:
             context: .
             push: true
             tags: om1001/runpod-face-processing:gpu-enabled,om1001/runpod-face-processing:latest
   ```

3. **Agregar secrets en GitHub:**
   - Ve a tu repo → Settings → Secrets and variables → Actions
   - Agrega `DOCKERHUB_USERNAME` = `om1001`
   - Agrega `DOCKERHUB_TOKEN` = [genera token en hub.docker.com/settings/security]

4. **Ejecuta el workflow:**
   - Ve a Actions tab → Run workflow
   - GitHub build servers tienen mejor conexión a Docker Hub

### Opción B: Usar AWS EC2/Digital Ocean (Temporal)

```bash
# 1. En tu máquina local, exporta la imagen
docker save runpod-face-processing:latest | gzip > runpod-gpu.tar.gz

# 2. Sube a servidor temporal (usa EC2 free tier)
scp runpod-gpu.tar.gz ec2-user@your-server:/tmp/

# 3. En el servidor remoto:
ssh ec2-user@your-server

# Instalar Docker
sudo yum install -y docker
sudo service docker start

# Cargar y push
cd /tmp
gunzip -c runpod-gpu.tar.gz | docker load
docker login
docker tag runpod-face-processing:latest om1001/runpod-face-processing:gpu-enabled
docker push om1001/runpod-face-processing:gpu-enabled
```

## Solución 2: Usar RunPod Template Builder (MÁS RÁPIDO)

RunPod permite construir imágenes DIRECTAMENTE en su infraestructura:

### Pasos:

1. **Sube código a repositorio público:**
   - GitHub, GitLab, o Bitbucket
   - Asegúrate que `Dockerfile`, `app.py`, `requirements.txt` están en el root

2. **En RunPod Dashboard:**
   - Ve a "Serverless" → "Templates"
   - Click "New Template"
   - Selecciona "Build from Repository"
   - Repo URL: `https://github.com/YOUR-USERNAME/runpod-image-processing`
   - Branch: `main`
   - Dockerfile Path: `/Dockerfile`

3. **Configure Build:**
   - Container Disk: 10 GB
   - Enable "Build with GPU" ✓

4. **Click "Create Template"**
   - RunPod construirá la imagen en su infraestructura (más rápido)
   - Cuando termine, asigna el template a tu endpoint

### Ventajas:
- ✅ No necesitas Docker Hub
- ✅ Build en servidores de RunPod (más rápido)
- ✅ Auto-deployment cuando actualizas el repo
- ✅ Evita problemas de conexión local

## Solución 3: Update manual del código en RunPod

Si solo cambiaste `app.py` (como en este caso):

### Pasos:

1. **Accede al worker via SSH** (si RunPod lo permite en tu plan):
   ```bash
   runpod ssh <pod-id>
   ```

2. **Edita el archivo directamente:**
   ```bash
   cd /app
   nano app.py
   # Pega el código actualizado
   ```

3. **Reinicia el worker:**
   - En RunPod dashboard: Stop → Start

**Nota**: Esto NO es persistente - se perderá al recrear el worker.

## Solución 4: Usar registro alternativo

Si Docker Hub sigue fallando, usa otro registro:

### GitHub Container Registry (ghcr.io)

```bash
# Login a GitHub Container Registry
echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u YOUR-USERNAME --password-stdin

# Tag y push
docker tag runpod-face-processing:latest ghcr.io/YOUR-USERNAME/runpod-face-processing:gpu-enabled
docker push ghcr.io/YOUR-USERNAME/runpod-face-processing:gpu-enabled
```

**En RunPod endpoint:**
- Container Image: `ghcr.io/YOUR-USERNAME/runpod-face-processing:gpu-enabled`

### Alternativas:
- **AWS ECR**: Más rápido si tu RunPod worker está en AWS
- **Google Artifact Registry**: Buena opción para multi-region
- **Azure Container Registry**

## Recomendación

**Para tu caso específico:**

1. **Inmediato** (hoy): Usa **Solución 2** (RunPod Template Builder desde GitHub)
   - Es la más rápida y no requiere push manual
   - Tiempo estimado: 5-10 minutos

2. **Largo plazo**: Configura **Solución 1 Opción A** (GitHub Actions)
   - Auto-deploy en cada commit
   - CI/CD completo

## Verificación después del deployment

Una vez desplegado con cualquier método, verifica:

```bash
# Ver logs del worker en RunPod
# Debe mostrar:
=== GPU Diagnostics ===
ONNX Runtime providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']
CUDA available: True
InsightFace initialized with ctx_id=0 (GPU mode)
=======================
```

Si ves esto, el GPU está correctamente configurado. ✅
