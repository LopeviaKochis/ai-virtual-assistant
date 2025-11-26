FROM python:3.11-slim-bookworm

# Variables para mejor rendimiento
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn uvicorn

# Copiar la app (sin venv ni archivos pesados)
COPY . .

# Seguridad
# Crear un usuario sin privilegios y asignar permisos
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Comando de producción optimizado
# Ejecuta Gunicorn con Uvicorn como worker para servir la app FastAPI
# Ejecuta 3 workers para manejar múltiples solicitudes concurrentes
CMD ["gunicorn", "main:app", \
     "--workers", "3", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "60", \
     "--bind", "0.0.0.0:8000"]
