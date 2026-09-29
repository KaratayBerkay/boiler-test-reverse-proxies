# pxlab loadgen — every load-generation / protocol client used by the lab in ONE image, run on the proxy's
# docker network (published ports go through docker-proxy/NAT and would distort the numbers):
#   wrk (HTTP/1.1 reference), oha (HTTP/1.1 + HTTP/2, JSON, rate limiting), h2load (nghttp2: HTTP/1.1 + HTTP/2 multiplexing),
#   h3load (HTTP/3 - built here from shared/loadgen/h3load), fortio (open-loop fixed-QPS + gRPC health load),
#   k6 (WebSocket scenarios), curl, grpcurl, openssl, ab. (Debian curl has no HTTP/3: h3load covers it.)
FROM golang:1.26-alpine AS build
WORKDIR /src
COPY h3load/go.mod ./
COPY h3load/main.go ./
RUN go get github.com/quic-go/quic-go@latest && go mod tidy && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /h3load . \
 && go list -m github.com/quic-go/quic-go > /quic-go.version
RUN GOBIN=/out go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

FROM debian:trixie-slim
# glibc base: the oha binary copied from ghcr.io/hatoo/oha is dynamically linked against glibc (it does not start on Alpine)
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends wrk nghttp2-client curl openssl apache2-utils jq dnsutils netcat-openbsd ca-certificates procps \
 && rm -rf /var/lib/apt/lists/*
COPY --from=fortio/fortio:latest /usr/bin/fortio /usr/local/bin/fortio
COPY --from=grafana/k6:latest /usr/bin/k6 /usr/local/bin/k6
COPY --from=ghcr.io/hatoo/oha:latest /bin/oha /usr/local/bin/oha
COPY --from=build /h3load /usr/local/bin/h3load
COPY --from=build /out/grpcurl /usr/local/bin/grpcurl
COPY --from=build /quic-go.version /etc/quic-go.version
COPY k6 /k6
WORKDIR /work
CMD ["bash"]
