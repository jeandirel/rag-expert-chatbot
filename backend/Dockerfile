# ── Build stage ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    build-essential \
        libmagic1 \
            poppler-utils \
                tesseract-ocr \
                    tesseract-ocr-fra \
                        libreoffice \
                            && rm -rf /var/lib/apt/lists/*

                            COPY requirements.txt .
                            RUN pip install --no-cache-dir --user -r requirements.txt

                            # ── Production stage ────────────────────────────────────────────
                            FROM python:3.11-slim AS production

                            WORKDIR /app

                            RUN apt-get update && apt-get install -y \
                                libmagic1 \
                                    poppler-utils \
                                        tesseract-ocr \
                                            tesseract-ocr-fra \
                                                curl \
                                                    && rm -rf /var/lib/apt/lists/*

                                                    COPY --from=builder /root/.local /root/.local
                                                    ENV PATH=/root/.local/bin:$PATH

                                                    COPY . .

                                                    RUN mkdir -p /app/documents /app/logs

                                                    ENV PYTHONPATH=/app
                                                    ENV PYTHONDONTWRITEBYTECODE=1
                                                    ENV PYTHONUNBUFFERED=1

                                                    EXPOSE 8000

                                                    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
                                                        CMD curl -f http://localhost:8000/health || exit 1

                                                        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
