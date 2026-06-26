# Use the official Python 3.14 release-candidate slim base image
FROM python:3.14-rc-slim

# Set environment variables to prevent pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set the container workspace directory
WORKDIR /workspace

# Install required system tools and clean up apt cache to keep image small
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    openssh-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and building tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements file first to leverage Docker build cache
COPY requirements.txt /workspace/

# Create a non-root user
ARG UID=1000
ARG GID=1000
RUN groupadd -g "${GID}" devuser && \
    useradd -l -u "${UID}" -g devuser -m devuser -s /bin/bash && \
    chown -R devuser:devuser /workspace

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Switch to the new user
USER devuser
ENV HOME=/home/devuser
ENV PATH="/home/devuser/.local/bin:${PATH}"

# Install Antigravity CLI as devuser
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash

# Copy the agentic runner script
COPY --chown=devuser:devuser run_agent.py /workspace/run_agent.py

# Expose FastAPI default port
EXPOSE 8000

# Default command keeps the container running in the background for development
CMD ["tail", "-f", "/dev/null"]
