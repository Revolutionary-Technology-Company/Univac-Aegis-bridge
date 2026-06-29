# ==========================================
# STAGE 1: Dependency Compiler Build Engine
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system compilation utilities for C++ and Python binding extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Cache and optimize python dependency compilation wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# STAGE 2: Hardened Runtime Containment Target
# ==========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install minimal dynamic runtime components (like networking utilities)
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Harvest isolated library packages directly from the build layer
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Mount application source codes into the deployment layout
COPY . .

# Expose target backplane communication interface channels 
EXPOSE 8080

# Configure execution constraints to maintain steady telemetry streaming frequencies
ENV PYTHONUNBUFFERED=1

# Execute the primary network layer service coordinator node
CMD ["python", "src/network_layer/async_typer_node.py"]
