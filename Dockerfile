FROM python:3.10

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
    fi && \
    rm ta-lib_0.6.4_amd64.deb ta-lib_0.6.4_arm64.deb

# Copiar archivos de requisitos
RUN mkdir logs

COPY ./requirements.txt ./
COPY ./script.py ./
COPY ./functions.py ./
COPY ./config.py ./
COPY ./indicators.py ./
COPY ./sr.py ./

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "script.py"]
