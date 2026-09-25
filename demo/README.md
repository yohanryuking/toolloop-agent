# Grabar el demo sin gastar API key real

Este directorio graba un video de la app haciendo la tarea completa del
brief (clima → evento al aire libre → aviso por email) sin necesitar una
`ANTHROPIC_API_KEY` real: `backend/scripts/demo_server.py` levanta el backend
de verdad (SQLite real, tools reales) pero con el cliente LLM reemplazado por
uno que sigue un guion fijo.

## Cómo correrlo

Tres terminales:

```bash
# 1. Backend con LLM simulado
cd backend
source .venv/bin/activate  # o el venv que uses
python -m scripts.demo_server

# 2. Frontend apuntando a ese backend
cd frontend
VITE_API_URL=http://localhost:8010 npm run dev

# 3. Grabar
cd demo
npm install
node record.js
```

El video queda en `demo/videos/*.webm`. Es un formato estándar (Chrome,
Firefox, VLC, YouTube y LinkedIn lo aceptan); si preferís mp4, convertilo con
`ffmpeg -i video.webm -c:v libx264 -pix_fmt yuv420p video.mp4` (necesita un
ffmpeg con soporte de H.264, no siempre viene en builds mínimos).

## Variables de entorno útiles

- `DEMO_APP_URL`: URL del frontend (default `http://localhost:5173`).
- `DEMO_TASK_MESSAGE`: el mensaje que se le manda al agente (default, la
  tarea del brief).
- `DEMO_CHROMIUM_PATH`: ruta a un binario de Chromium preinstalado, para
  sandboxes donde Playwright no puede descargar el suyo propio. En el
  entorno donde se grabó originalmente este demo:
  `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- `DEMO_PORT` (para `demo_server.py`): puerto del backend demo (default
  `8010`).

## Por qué existe esto

Grabar el video del Sprint 6 (ver `docs/ROADMAP.md`) no debería depender de
gastar créditos de la API de Anthropic ni de tener el deploy real ya hecho.
Este harness deja el video reproducible en cualquier momento — antes del
deploy, después, o para volver a grabarlo si cambia la UI.
