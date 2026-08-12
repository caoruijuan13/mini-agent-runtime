# ─── Build stage ──────────────────────────────────────────────────────────────
FROM rust:1.77-slim AS builder

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src/ ./src/

RUN cargo build --release

# ─── Runtime stage ────────────────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy server binary
COPY --from=builder /app/target/release/mini-agent-server /usr/local/bin/

# Copy Python agent
COPY python/ ./python/
COPY python/requirements.txt ./python/requirements.txt

# Install Python dependencies
RUN pip3 install --no-cache-dir -r python/requirements.txt

# Copy scripts
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh

# Environment defaults
ENV HOST=0.0.0.0
ENV PORT=3000
ENV LLM_PROVIDER=mock
ENV RUST_LOG=mini_agent_server=info

EXPOSE 3000

# Start server by default
CMD ["mini-agent-server"]
