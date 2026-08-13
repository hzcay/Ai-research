# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=1000

COPY requirements/ requirements/

FROM runtime AS ml-runtime
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url https://download.pytorch.org/whl/cpu torch

FROM ml-runtime AS api
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements/api.txt

COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8000
CMD ["/entrypoint.sh"]

FROM ml-runtime AS worker
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libxcb1 \
    libxcb-render0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements/worker.txt
COPY . .
CMD ["arq", "src.worker.WorkerSettings"]

FROM node:22-alpine AS ui
WORKDIR /app
COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]

FROM worker AS dev
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements/dev.txt
