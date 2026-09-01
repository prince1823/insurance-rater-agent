# Build context must be the repo's `rateragent/` directory (so `data/` is available):
#   docker build -f backend/Dockerfile -t rater .
# On Render: Root Directory = rateragent, Dockerfile Path = backend/Dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./
COPY data/ /data/

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
