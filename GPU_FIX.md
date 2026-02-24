# Solución: RunPod usando CPU en lugar de GPU

## Problema
El worker de RunPod muestra 0% de uso de GPU (ver telemetría) a pesar de tener una RTX A5000 asignada.

## Causa
El código está configurado correctamente (`ctx_id=0`), el Dockerfile usa imagen CUDA, y requirements.txt tiene `onnxruntime-gpu`. Sin embargo, la imagen Docker actual en RunPod no tiene los diagnósticos necesarios.

## Solución 1: Actualizar imagen Docker (Recomendado)

### Pasos:

1. **Verificar que la imagen local esté construida:**
   ```bash
   docker images | grep runpod-face-processing
   # Debería mostrar: runpod-face-processing latest 517c6e2e46a8 ...
   ```

2. **Push manual con reintentos:**
   Si tienes problemas de red, usa el siguiente comando que reintenta automáticamente:
   ```bash
   # Tag la imagen
   docker tag runpod-face-processing:latest om1001/runpod-face-processing:gpu-enabled

   # Push con reintentos
   until docker push om1001/runpod-face-processing:gpu-enabled; do
     echo "Push failed, retrying in 10s..."
     sleep 10
   done
   ```

3. **Actualizar endpoint en RunPod:**
   - Ve a tu endpoint: https://runpod.io/console/serverless
   - Click en tu endpoint `runpod-image-processing`
   - En "Container Configuration" → "Container Image" cambia a:
     ```
     om1001/runpod-face-processing:gpu-enabled
     ```
   - Guarda cambios
   - Espera a que se reinicie el worker (~2-3 min)

4. **Verificar logs de inicio:**
   - En RunPod dashboard, ve a "Logs" tab
   - Busca estas líneas en el startup:
     ```
     === GPU Diagnostics ===
     ONNX Runtime providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']
     CUDA available: True
     InsightFace initialized with ctx_id=0 (GPU mode)
     =======================
     ```

## Solución 2: Push desde máquina con mejor conexión

Si el push desde WSL falla por red lenta:

```bash
# 1. Guardar la imagen como archivo
docker save runpod-face-processing:latest | gzip > runpod-gpu-fix.tar.gz

# 2. Transferir a máquina con mejor internet (AWS EC2, etc.)
scp runpod-gpu-fix.tar.gz user@server:/tmp/

# 3. En el servidor remoto:
docker load < /tmp/runpod-gpu-fix.tar.gz
docker tag runpod-face-processing:latest om1001/runpod-face-processing:gpu-enabled
docker push om1001/runpod-face-processing:gpu-enabled
```

## Solución 3: Verificar configuración de RunPod

A veces el problema NO es la imagen, sino la configuración del worker:

1. **Verificar GPU asignada:**
   - En RunPod dashboard → "Workers" → verifica que muestre "RTX A5000" o similar
   - Si muestra "CPU-only", cambia a un worker con GPU

2. **Verificar volumen de datos:**
   - Los modelos de InsightFace se descargan en `/root/.insightface/`
   - Si el worker no tiene volumen persistente, descarga el modelo cada vez (lento)
   - Solución: agregar Network Volume en RunPod y montar en `/root/.insightface/`

3. **Verificar timeout:**
   - GPU initialization puede tardar 10-15s en primera ejecución
   - Asegúrate que el timeout del endpoint sea >= 30s

## ¿Cómo verificar que se está usando GPU?

### Método 1: Logs de RunPod
Busca en los logs del worker (tab "Logs"):
```
InsightFace initialized with ctx_id=0 (GPU mode)
CUDA available: True
```

### Método 2: Telemetría
- La gráfica "RTX A5000 → Utilization" debe mostrar >0% durante el procesamiento
- Si procesas un batch de 10+ imágenes y sigue en 0%, hay un problema

### Método 3: Performance
- **GPU mode**: Batch de 100 imágenes = ~2-3 minutos
- **CPU mode**: Batch de 100 imágenes = ~60+ minutos

## Cambios realizados

Los siguientes archivos fueron modificados para agregar diagnósticos:

- [app.py:15-24](app.py#L15-L24) - Agregados prints de diagnóstico GPU

## Próximos pasos

1. Ejecuta el push de la nueva imagen
2. Actualiza el endpoint en RunPod
3. Ejecuta un test request y verifica:
   - Los logs muestran "CUDA available: True"
   - La telemetría muestra uso de GPU >0%
   - El tiempo de procesamiento es rápido (~2-3 min para 100 imágenes)

Si después de esto sigue usando CPU, el problema está en la configuración de RunPod, no en el código.
