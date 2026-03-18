# Minimal fractal-cellpose-sam wrapper container - CPU only
FROM ubuntu:22.04

# Build arguments
ARG VERSION=0.1.0

# Set environment variables to prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install minimal dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        build-essential \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Install pixi and set up fractal environment
RUN curl -fsSL https://pixi.sh/install.sh | bash
ENV PATH="/root/.pixi/bin:$PATH"

# Set up application directory
WORKDIR /app
COPY . /app/

# Set version for setuptools-scm
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_FRACTAL_TASK_INTEROPERABILITY=${VERSION}

# Install fractal dependencies
RUN pixi install

# Simple entrypoint: use direct Python path for Singularity compatibility
ENTRYPOINT ["/app/.pixi/envs/default/bin/python", "/app/wrapper.py"]
CMD []