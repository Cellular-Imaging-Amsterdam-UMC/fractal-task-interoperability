# Use Ubuntu base with conda for environment management (following W_Segmentation-Cellpose4 pattern)
FROM ubuntu:22.04

# Set environment variables to prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PATH=/opt/conda/bin:$PATH

# Install base dependencies and cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        git \
        bzip2 \
        ca-certificates \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgeos-dev \
        libgl1-mesa-dev \
        build-essential \
        curl \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -a -y && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    conda init bash

# Make conda available in RUN instructions using the initialized shell
SHELL ["/bin/bash", "--login", "-c"]

# Accept conda channels terms & conditions
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
RUN conda config --add channels conda-forge && conda config --set channel_priority strict

# Update conda
RUN conda update -n base -c defaults conda --yes

# ------------------------------------------------------------------------------
# Create BIAFLOWS/Cytomine environment (Python 3.7 for compatibility)
# ------------------------------------------------------------------------------
ENV CYTOMINE_ENV_NAME=cytomine_py37
RUN conda create -n $CYTOMINE_ENV_NAME python=3.7 -y

# Install BIAFLOWS utilities in the cytomine environment
RUN conda run -n $CYTOMINE_ENV_NAME pip install --no-cache-dir \
        git+https://github.com/cytomine-uliege/Cytomine-python-client.git@v2.7.3

RUN conda run -n $CYTOMINE_ENV_NAME pip install --no-cache-dir \
        git+https://github.com/Neubias-WG5/biaflows-utilities.git@v0.9.2

# ------------------------------------------------------------------------------
# Install pixi and set up fractal environment
# ------------------------------------------------------------------------------
RUN curl -fsSL https://pixi.sh/install.sh | bash
ENV PATH="/root/.pixi/bin:$PATH"

# Set up application directory for fractal (BIAFLOWS standard)
WORKDIR /app
COPY . /app/

# Run pixi install to get all fractal dependencies in pixi environment
RUN pixi install

# Clean up conda cache
RUN conda clean -a -y

# ------------------------------------------------------------------------------
# Application Code & Entrypoint (files already copied above)
# ------------------------------------------------------------------------------
# Already in /app and files are copied

# Entrypoint runs wrapper in cytomine environment (simplified - only wrapper.py)
ENTRYPOINT ["bash", "-c", "source /opt/conda/etc/profile.d/conda.sh && conda activate cytomine_py37 && exec python /app/wrapper.py \"$@\"", "--"]
CMD []