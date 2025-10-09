FROM python:3.12-slim AS builder

WORKDIR /code

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    chromium \
    chromium-driver \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt

RUN pip install --upgrade pip setuptools; \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM techins8pro/profile-scrapper:builder AS app

WORKDIR /code

# Create a non-root user and setup chrome directories
RUN useradd -m -u 1000 chrome && \
    # Create necessary directories
    mkdir -p /data && \
    mkdir -p /home/chrome/.config/chromium && \
    mkdir -p /home/chrome/.cache/chromium && \
    # Give chrome user access to chromedriver and directories
    chmod 777 /usr/bin/chromedriver && \
    chown -R chrome:chrome /data /home/chrome && \
    # Add chrome to video group for display access
    usermod -aG video chrome

# Set Chrome executable path and other env vars
ENV CHROME_EXECUTABLE_PATH=/usr/bin/chromium
ENV PATH="/code/.local/bin:${PATH}"
ENV PYTHONPATH=/code
ENV DISPLAY=:99
ENV HOME=/home/chrome

# Copy application files
COPY . /code
RUN chown -R chrome:chrome /code

# Install dependencies as chrome user
USER chrome
RUN pip install --user --no-cache-dir -r requirements.txt && \
    mkdir -p migrations/versions

EXPOSE 80

# Start Xvfb and the application
CMD Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & \
    uvicorn app.api:app --host 0.0.0.0 --port 80 --reload