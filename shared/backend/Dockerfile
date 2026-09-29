# pxlab backend — the origin server behind every proxy in the lab (HTTP/1.1 + h2c, PROXY protocol, TLS, gRPC, UDP).
FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY main.go ./
RUN go mod tidy && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /backend .

FROM alpine:3.22
RUN apk add --no-cache ca-certificates curl
COPY --from=build /backend /usr/local/bin/backend
EXPOSE 8080 8081 8443 9090 9002/udp
HEALTHCHECK --interval=3s --timeout=2s --retries=10 CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1
ENTRYPOINT ["/usr/local/bin/backend"]
