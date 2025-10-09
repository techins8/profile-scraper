# syntax=docker/dockerfile:1.4
FROM python:3.12-slim AS builder

WORKDIR /code

# Install uv - ultra fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    chromium \
    chromium-driver \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies with uv into a virtual environment
# This is cached by Docker and only re-runs when pyproject.toml or uv.lock change
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim AS app

WORKDIR /code

# Install runtime system dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    chromium \
    chromium-driver \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and setup chrome directories
RUN useradd -m -u 1000 chrome && \
    mkdir -p /data && \
    mkdir -p /home/chrome/.config/chromium && \
    mkdir -p /home/chrome/.cache/chromium && \
    chmod 777 /usr/bin/chromedriver && \
    chown -R chrome:chrome /data /home/chrome && \
    usermod -aG video chrome

# Copy virtual environment from builder
COPY --from=builder --chown=chrome:chrome /code/.venv /code/.venv

# Set Chrome executable path and other env vars
ENV CHROME_EXECUTABLE_PATH=/usr/bin/chromium
ENV PATH="/code/.venv/bin:${PATH}"
ENV PYTHONPATH=/code
ENV DISPLAY=:99
ENV HOME=/home/chrome

# Copy application files
COPY --chown=chrome:chrome . /code
RUN mkdir -p migrations/versions && chown -R chrome:chrome /code

USER chrome

EXPOSE 80

# Start Xvfb and the application
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & /code/.venv/bin/uvicorn app.api:app --host 0.0.0.0 --port 80 --reload"]
