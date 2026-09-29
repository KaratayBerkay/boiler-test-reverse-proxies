# pingora-lab: a reverse proxy written in Rust on Cloudflare's Pingora framework (see src/main.rs).
FROM rust:1-slim AS build
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends pkg-config libssl-dev cmake perl make g++ && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY Cargo.toml Cargo.lock* ./
COPY src ./src
RUN cargo build --release --locked 2>/dev/null || cargo build --release

FROM debian:trixie-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends libssl3t64 ca-certificates curl procps && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/target/release/pingora-lab /usr/local/bin/pingora-lab
EXPOSE 80 8080 8443 8444 9000 9100 9101
# PID 1 is a shell so that a zero-downtime upgrade (new process with -u, SIGQUIT to the old one) does not stop the container
CMD ["sh", "-c", "pingora-lab -c /etc/pingora/config.yaml; while true; do sleep 3600; done"]
