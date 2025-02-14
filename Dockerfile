FROM python:3.10

WORKDIR /app

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

RUN mkdir logs

COPY ./requirements.txt ./
COPY ./script.py ./
COPY ./functions.py ./
COPY ./config.py ./
COPY ./indicators.py ./
COPY ./test_soportes_resistencias.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "script.py"]
