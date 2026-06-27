# DID Intel — production Docker image
# Build:  docker build -t did-intel .
# Run:    docker run -p 8000:8000 did-intel
# Env:    DIDINTEL_API_HOST=0.0.0.0 DIDINTEL_API_PORT=8000
#         DIDINTEL_API_KEY_REQUIRED=true DIDINTEL_ALLOWED_API_KEYS=key1,key2

FROM python:3.12-slim

LABEL org.opencontainers.image.title="DID Intel"
LABEL org.opencontainers.image.description="Phone number reputation scraper and API"
LABEL org.opencontainers.image.url="https://github.com/siamakanda/DIDRepChecker"

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
RUN pip install --no-cache-dir -e .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

ENTRYPOINT ["didintel-server"]
