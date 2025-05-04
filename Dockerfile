FROM python:3.10 AS builder

# Establecer variable de entorno para indicar que estamos en un contenedor Docker
ENV DOCKER_CONTAINER=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias para Matplotlib
RUN apt-get update && apt-get install -y \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para la aplicación
WORKDIR /app

# Crear directorio para los outputs
RUN mkdir -p /app/output

COPY ./ta-lib_0.6.4_amd64.deb ./ta-lib_0.6.4_arm64.deb ./

RUN apt-get update && apt-get install -y build-essential gcc curl git && \
    if [ "$(uname -m)" = "x86_64" ]; then \
        dpkg -i ta-lib_0.6.4_amd64.deb; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        dpkg -i ta-lib_0.6.4_arm64.deb; \
    else \
        echo "Unsupported architecture"; exit 1; \
    fi

# Instalar dependencias
COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -t /python_dependencies


FROM python:3.10-slim

# Mantener variables de entorno consistentes
ENV DOCKER_CONTAINER=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar TA-Lib directamente en la imagen final
COPY ./ta-lib_0.6.4_amd64.deb ./ta-lib_0.6.4_arm64.deb ./
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libpng16-16 \
    && \
    if [ "$(uname -m)" = "x86_64" ]; then \
        dpkg -i ta-lib_0.6.4_amd64.deb || apt-get -f install -y; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        dpkg -i ta-lib_0.6.4_arm64.deb || apt-get -f install -y; \
    else \
        echo "Unsupported architecture"; exit 1; \
    fi && \
    rm ta-lib_0.6.4_amd64.deb ta-lib_0.6.4_arm64.deb && \
    rm -rf /var/lib/apt/lists/* && \
    ldconfig

# Crear directorios para logs y outputs
RUN mkdir -p /app/logs /app/output && chmod 777 /app/logs /app/output

# Copiar las dependencias de Python
COPY --from=builder /python_dependencies /usr/local/lib/python3.10/site-packages/

# Copiar archivos de código fuente
COPY ./scripts/*.py ./

# Verificar que TA-Lib está correctamente instalado
RUN ls -la /usr/lib/libta*

CMD ["python", "script.py"]