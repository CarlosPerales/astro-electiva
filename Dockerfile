# ═══════════════════════════════════════════════════════════════════════════════
# DOCKERFILE - ASTROLOGÍA ELECTIVA EMPRESARIAL
# ═══════════════════════════════════════════════════════════════════════════════
# API para calcular fechas óptimas de lanzamiento empresarial
# Metodología: Vivian E. Robson - "Electional Astrology"
# Motor: Swiss Ephemeris
# ═══════════════════════════════════════════════════════════════════════════════

# Imagen base: Python 3.11 versión ligera
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Variables de entorno para optimizar Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias para compilar pyswisseph
# gcc y g++ son requeridos para compilar la librería de Swiss Ephemeris
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación
COPY . .

# Puerto por defecto (Railway asigna su propio puerto via variable $PORT)
EXPOSE 8000

# ═══════════════════════════════════════════════════════════════════════════════
# COMANDO DE INICIO
# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTANTE: Usar formato shell (sin corchetes) para que ${PORT} se interprete
# Railway inyecta la variable PORT automáticamente
# Si PORT no existe, usa 8000 por defecto
# ═══════════════════════════════════════════════════════════════════════════════
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}