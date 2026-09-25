FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Directorio para el archivo SQLite. Si se monta un volumen persistente acá
# (ver fly.toml o docker-compose.yml), la base sobrevive a reinicios.
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
