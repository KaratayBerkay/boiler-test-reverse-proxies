// pxlab backend: the origin every reverse proxy in the lab points at.
//
// One binary, five listeners, all configured by environment variables:
//
//	:8080  HTTP/1.1 + h2c (prior knowledge)      echo / delay / status / size / cache / auth / ws / sse / admin
//	:8081  same HTTP server behind PROXY protocol v1/v2 (the echo reports the PROXY source address)
//	:8443  same HTTP server over TLS (HTTP/1.1 + h2 via ALPN; cert from shared/certs)
//	:9090  gRPC (grpc.health.v1.Health + reflection) over h2c
//	:9002  UDP echo
//
// INSTANCE / POOL name the instance (returned in every response as X-Instance / X-Pool and in the echo JSON),
// DELAY_MS adds a fixed delay to every request (the "slow" instance), FAIL_RATE makes a fraction of requests
// fail with 500 (the "flaky" instance). Both can be changed at run time through /admin/*.
package main

import (
	"bufio"
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha1"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"math/big"
	mrand "math/rand"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/pires/go-proxyproto"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
)

var (
	instance = env("INSTANCE", "app")
	pool     = env("POOL", "app")
	version  = "1.0"

	healthy   atomic.Bool
	failRate  atomic.Value // float64
	failCode  atomic.Int64
	delayMs   atomic.Int64
	reqTotal  atomic.Int64
	connTotal atomic.Int64
	wsMsgs    atomic.Int64
	pathHits  sync.Map // path -> *atomic.Int64
	startedAt = time.Now()
	lorem     = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua "
)

type ctxKey int

const (
	ctxListener ctxKey = iota
	ctxProxyHeader
	ctxConnID
)

func env(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func envInt(k string, d int64) int64 {
	if v := os.Getenv(k); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil {
			return n
		}
	}
	return d
}

func envFloat(k string, d float64) float64 {
	if v := os.Getenv(k); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			return f
		}
	}
	return d
}

func main() {
	healthy.Store(true)
	failRate.Store(envFloat("FAIL_RATE", 0))
	failCode.Store(envInt("FAIL_CODE", 500))
	delayMs.Store(envInt("DELAY_MS", 0))

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", handleHealth)
	mux.HandleFunc("/admin/health", handleAdminHealth)
	mux.HandleFunc("/admin/fail", handleAdminFail)
	mux.HandleFunc("/admin/delay", handleAdminDelay)
	mux.HandleFunc("/admin/stats", handleAdminStats)
	mux.HandleFunc("/admin/reset", handleAdminReset)
	mux.HandleFunc("/delay/", handleDelay)
	mux.HandleFunc("/status/", handleStatus)
	mux.HandleFunc("/size/", handleSize)
	mux.HandleFunc("/bin/", handleBin)
	mux.HandleFunc("/small", handleSmall)
	mux.HandleFunc("/cacheable/", handleCacheable(60))
	mux.HandleFunc("/cacheable-short/", handleCacheable(2))
	mux.HandleFunc("/upload", handleUpload)
	mux.HandleFunc("/auth", handleAuth)
	mux.HandleFunc("/auth/", handleAuth) // ext_authz-style clients append the original path
	mux.HandleFunc("/ws", handleWS)
	mux.HandleFunc("/sse", handleSSE)
	mux.HandleFunc("/", handleEcho)
	h := middleware(mux)

	var wg sync.WaitGroup
	serve := func(name string, fn func() error) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := fn(); err != nil && !errors.Is(err, http.ErrServerClosed) {
				log.Fatalf("%s: %v", name, err)
			}
		}()
	}
	serve("http", func() error { return serveHTTP(env("HTTP_ADDR", ":8080"), "http", h, nil, false) })
	serve("pp", func() error { return serveHTTP(env("PP_ADDR", ":8081"), "pp", h, nil, true) })
	serve("tls", func() error { return serveHTTP(env("TLS_ADDR", ":8443"), "tls", h, tlsConfig(), false) })
	serve("grpc", func() error { return serveGRPC(env("GRPC_ADDR", ":9090")) })
	serve("udp", func() error { return serveUDP(env("UDP_ADDR", ":9002")) })
	log.Printf("pxlab backend %s instance=%s pool=%s delay=%dms fail_rate=%v", version, instance, pool, delayMs.Load(), failRate.Load())
	wg.Wait()
}

// ---------------------------------------------------------------------------------------------- listeners

func serveHTTP(addr, name string, h http.Handler, tc *tls.Config, pp bool) error {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	if pp {
		ln = &proxyproto.Listener{Listener: ln, ReadHeaderTimeout: 10 * time.Second}
	}
	if tc != nil {
		ln = tls.NewListener(ln, tc)
	}
	srv := &http.Server{
		Handler:           h,
		ReadHeaderTimeout: 30 * time.Second,
		IdleTimeout:       120 * time.Second,
		ConnState: func(c net.Conn, s http.ConnState) {
			if s == http.StateNew {
				connTotal.Add(1)
			}
		},
		ConnContext: func(ctx context.Context, c net.Conn) context.Context {
			ctx = context.WithValue(ctx, ctxListener, name)
			ctx = context.WithValue(ctx, ctxConnID, connTotal.Load())
			if pc, ok := c.(*proxyproto.Conn); ok {
				ctx = context.WithValue(ctx, ctxProxyHeader, pc.ProxyHeader())
			}
			return ctx
		},
	}
	// HTTP/1.1 and cleartext HTTP/2 (prior knowledge) on the same port; TLS gets h2 through ALPN.
	srv.Protocols = new(http.Protocols)
	srv.Protocols.SetHTTP1(true)
	srv.Protocols.SetHTTP2(true)
	srv.Protocols.SetUnencryptedHTTP2(true)
	if tc != nil {
		srv.TLSConfig = tc
	}
	log.Printf("listening %s on %s", name, addr)
	return srv.Serve(ln)
}

func tlsConfig() *tls.Config {
	certFile, keyFile := env("TLS_CERT", "/certs/backend.crt"), env("TLS_KEY", "/certs/backend.key")
	cert, err := tls.LoadX509KeyPair(certFile, keyFile)
	if err != nil {
		log.Printf("no cert at %s (%v): generating a self-signed one", certFile, err)
		cert = selfSigned()
	}
	return &tls.Config{Certificates: []tls.Certificate{cert}, MinVersion: tls.VersionTLS12, NextProtos: []string{"h2", "http/1.1"}}
}

func selfSigned() tls.Certificate {
	key, _ := rsa.GenerateKey(rand.Reader, 2048)
	tmpl := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "backend.lab"}, DNSNames: []string{"backend.lab", instance},
		NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(24 * 365 * time.Hour), KeyUsage: x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
	der, _ := x509.CreateCertificate(rand.Reader, tmpl, tmpl, &key.PublicKey, key)
	return tls.Certificate{Certificate: [][]byte{der}, PrivateKey: key}
}

func serveGRPC(addr string) error {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	s := grpc.NewServer()
	hs := health.NewServer()
	hs.SetServingStatus("", healthpb.HealthCheckResponse_SERVING)
	hs.SetServingStatus("lab.Echo", healthpb.HealthCheckResponse_SERVING)
	healthpb.RegisterHealthServer(s, hs)
	reflection.Register(s)
	log.Printf("listening grpc on %s", addr)
	return s.Serve(ln)
}

func serveUDP(addr string) error {
	pc, err := net.ListenPacket("udp", addr)
	if err != nil {
		return err
	}
	log.Printf("listening udp on %s", addr)
	buf := make([]byte, 65535)
	for {
		n, from, err := pc.ReadFrom(buf)
		if err != nil {
			return err
		}
		reply := append([]byte("echo:"+instance+":"), buf[:n]...)
		_, _ = pc.WriteTo(reply, from)
	}
}

// ---------------------------------------------------------------------------------------------- middleware

func middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Server", "lab-backend/"+version)
		w.Header().Set("X-Powered-By", "lab-backend")
		w.Header().Set("X-Instance", instance)
		w.Header().Set("X-Pool", pool)
		if strings.HasPrefix(r.URL.Path, "/admin/") || r.URL.Path == "/healthz" {
			next.ServeHTTP(w, r)
			return
		}
		reqTotal.Add(1)
		c, _ := pathHits.LoadOrStore(r.URL.Path, new(atomic.Int64))
		c.(*atomic.Int64).Add(1)
		if d := delayMs.Load(); d > 0 {
			time.Sleep(time.Duration(d) * time.Millisecond)
		}
		if fr := failRate.Load().(float64); fr > 0 && mrand.Float64() < fr {
			w.Header().Set("Cache-Control", "no-store")
			http.Error(w, fmt.Sprintf("injected failure from %s\n", instance), int(failCode.Load()))
			return
		}
		next.ServeHTTP(w, r)
	})
}

// ---------------------------------------------------------------------------------------------- handlers

type echo struct {
	Instance      string            `json:"instance"`
	Pool          string            `json:"pool"`
	Listener      string            `json:"listener"`
	Method        string            `json:"method"`
	Path          string            `json:"path"`
	RawQuery      string            `json:"raw_query"`
	Proto         string            `json:"proto"`
	Host          string            `json:"host"`
	RemoteAddr    string            `json:"remote_addr"`
	RequestID     string            `json:"request_id,omitempty"`
	BodyLen       int64             `json:"body_len"`
	ConnID        int64             `json:"conn_id"`
	TLS           *tlsInfo          `json:"tls,omitempty"`
	ProxyProtocol *ppInfo           `json:"proxy_protocol,omitempty"`
	Headers       map[string]string `json:"headers"`
}

type tlsInfo struct {
	Version string `json:"version"`
	SNI     string `json:"sni"`
	ALPN    string `json:"alpn"`
}

type ppInfo struct {
	Version  int    `json:"version"`
	SrcIP    string `json:"src_ip"`
	SrcPort  int    `json:"src_port"`
	DstIP    string `json:"dst_ip"`
	DstPort  int    `json:"dst_port"`
	Protocol string `json:"protocol"`
}

func buildEcho(r *http.Request, bodyLen int64) echo {
	e := echo{Instance: instance, Pool: pool, Method: r.Method, Path: r.URL.Path, RawQuery: r.URL.RawQuery, Proto: r.Proto, Host: r.Host,
		RemoteAddr: r.RemoteAddr, RequestID: r.Header.Get("X-Request-Id"), BodyLen: bodyLen, Headers: map[string]string{}}
	if v, ok := r.Context().Value(ctxListener).(string); ok {
		e.Listener = v
	}
	if v, ok := r.Context().Value(ctxConnID).(int64); ok {
		e.ConnID = v
	}
	if r.TLS != nil {
		e.TLS = &tlsInfo{Version: tlsVersion(r.TLS.Version), SNI: r.TLS.ServerName, ALPN: r.TLS.NegotiatedProtocol}
	}
	if hdr, ok := r.Context().Value(ctxProxyHeader).(*proxyproto.Header); ok && hdr != nil {
		p := &ppInfo{Version: int(hdr.Version), Protocol: fmt.Sprintf("0x%02x", byte(hdr.TransportProtocol))}
		if a, ok := hdr.SourceAddr.(*net.TCPAddr); ok {
			p.SrcIP, p.SrcPort = a.IP.String(), a.Port
		}
		if a, ok := hdr.DestinationAddr.(*net.TCPAddr); ok {
			p.DstIP, p.DstPort = a.IP.String(), a.Port
		}
		e.ProxyProtocol = p
	}
	for k, vs := range r.Header {
		e.Headers[k] = strings.Join(vs, ", ")
	}
	return e
}

func tlsVersion(v uint16) string {
	switch v {
	case tls.VersionTLS10:
		return "TLS1.0"
	case tls.VersionTLS11:
		return "TLS1.1"
	case tls.VersionTLS12:
		return "TLS1.2"
	case tls.VersionTLS13:
		return "TLS1.3"
	}
	return fmt.Sprintf("0x%04x", v)
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	enc := json.NewEncoder(w)
	enc.SetIndent("", " ")
	_ = enc.Encode(v)
}

func handleEcho(w http.ResponseWriter, r *http.Request) {
	n, _ := io.Copy(io.Discard, r.Body)
	w.Header().Set("Cache-Control", "no-store")
	writeJSON(w, 200, buildEcho(r, n))
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	if !healthy.Load() {
		http.Error(w, "unhealthy (toggled via /admin/health?state=down)\n", 503)
		return
	}
	w.Header().Set("Content-Type", "text/plain")
	_, _ = io.WriteString(w, "ok\n")
}

func handleAdminHealth(w http.ResponseWriter, r *http.Request) {
	switch r.URL.Query().Get("state") {
	case "up":
		healthy.Store(true)
	case "down":
		healthy.Store(false)
	}
	writeJSON(w, 200, map[string]any{"instance": instance, "healthy": healthy.Load()})
}

func handleAdminFail(w http.ResponseWriter, r *http.Request) {
	if v := r.URL.Query().Get("rate"); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			failRate.Store(f)
		}
	}
	if v := r.URL.Query().Get("code"); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil {
			failCode.Store(n)
		}
	}
	writeJSON(w, 200, map[string]any{"instance": instance, "fail_rate": failRate.Load(), "fail_code": failCode.Load()})
}

func handleAdminDelay(w http.ResponseWriter, r *http.Request) {
	if v := r.URL.Query().Get("ms"); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil {
			delayMs.Store(n)
		}
	}
	writeJSON(w, 200, map[string]any{"instance": instance, "delay_ms": delayMs.Load()})
}

func handleAdminStats(w http.ResponseWriter, r *http.Request) {
	paths := map[string]int64{}
	pathHits.Range(func(k, v any) bool {
		paths[k.(string)] = v.(*atomic.Int64).Load()
		return true
	})
	writeJSON(w, 200, map[string]any{"instance": instance, "pool": pool, "requests_total": reqTotal.Load(), "connections_total": connTotal.Load(),
		"ws_messages": wsMsgs.Load(), "healthy": healthy.Load(), "fail_rate": failRate.Load(), "delay_ms": delayMs.Load(),
		"uptime_s": int(time.Since(startedAt).Seconds()), "paths": paths})
}

func handleAdminReset(w http.ResponseWriter, r *http.Request) {
	reqTotal.Store(0)
	connTotal.Store(0)
	wsMsgs.Store(0)
	pathHits.Range(func(k, _ any) bool { pathHits.Delete(k); return true })
	writeJSON(w, 200, map[string]any{"instance": instance, "reset": true})
}

func handleDelay(w http.ResponseWriter, r *http.Request) {
	ms, _ := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/delay/"))
	if ms > 0 {
		select {
		case <-time.After(time.Duration(ms) * time.Millisecond):
		case <-r.Context().Done():
			return
		}
	}
	handleEcho(w, r)
}

func handleStatus(w http.ResponseWriter, r *http.Request) {
	code, _ := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/status/"))
	if code < 100 || code > 599 {
		code = 400
	}
	w.Header().Set("Content-Type", "text/plain")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(code)
	fmt.Fprintf(w, "status %d from %s\n", code, instance)
}

func handleSize(w http.ResponseWriter, r *http.Request) {
	n, _ := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/size/"))
	if n < 0 || n > 64<<20 {
		n = 1024
	}
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Header().Set("Content-Length", strconv.Itoa(n))
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(200)
	buf := []byte(strings.Repeat(lorem, 64))
	for n > 0 {
		k := n
		if k > len(buf) {
			k = len(buf)
		}
		if _, err := w.Write(buf[:k]); err != nil {
			return
		}
		n -= k
	}
}

var binChunk = func() []byte {
	b := make([]byte, 1<<20)
	rng := mrand.New(mrand.NewSource(42))
	for i := range b {
		b[i] = byte(rng.Intn(256))
	}
	return b
}()

func handleBin(w http.ResponseWriter, r *http.Request) {
	n, _ := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/bin/"))
	if n < 0 || n > 256<<20 {
		n = 1 << 20
	}
	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("Content-Length", strconv.Itoa(n))
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(200)
	for n > 0 {
		k := n
		if k > len(binChunk) {
			k = len(binChunk)
		}
		if _, err := w.Write(binChunk[:k]); err != nil {
			return
		}
		n -= k
	}
}

func handleSmall(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	fmt.Fprintf(w, `{"ok":true,"instance":"%s","pool":"%s","ts":%d,"msg":"small keep-alive response for throughput tests"}`+"\n", instance, pool, time.Now().UnixMilli())
}

var cacheCounters sync.Map

func handleCacheable(maxAge int) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		key := r.URL.Path
		c, _ := cacheCounters.LoadOrStore(key, new(atomic.Int64))
		n := c.(*atomic.Int64).Add(1)
		if r.Header.Get("X-Fail") == "1" {
			w.Header().Set("Cache-Control", "no-store")
			http.Error(w, "origin failure requested via X-Fail\n", 503)
			return
		}
		w.Header().Set("Cache-Control", fmt.Sprintf("public, max-age=%d, stale-while-revalidate=30, stale-if-error=300", maxAge))
		w.Header().Set("ETag", fmt.Sprintf(`"%s-%d"`, instance, n))
		w.Header().Set("Last-Modified", startedAt.UTC().Format(http.TimeFormat))
		w.Header().Set("X-Backend-Counter", strconv.FormatInt(n, 10))
		writeJSON(w, 200, map[string]any{"key": key, "counter": n, "instance": instance, "max_age": maxAge})
	}
}

func handleUpload(w http.ResponseWriter, r *http.Request) {
	n, _ := io.Copy(io.Discard, r.Body)
	w.Header().Set("Cache-Control", "no-store")
	writeJSON(w, 200, map[string]any{"instance": instance, "received": n, "method": r.Method})
}

// handleAuth is the external authorization service used by forward-auth / auth_request / ext_authz configs.
func handleAuth(w http.ResponseWriter, r *http.Request) {
	token := r.Header.Get("X-Auth-Token")
	if token == "" {
		token = strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
	}
	w.Header().Set("Cache-Control", "no-store")
	if token != "lab-secret" {
		w.Header().Set("WWW-Authenticate", `Bearer realm="pxlab"`)
		http.Error(w, "unauthorized: X-Auth-Token or Bearer must be lab-secret\n", 401)
		return
	}
	w.Header().Set("X-Auth-User", "alice")
	w.Header().Set("X-Auth-Groups", "lab,admin")
	w.WriteHeader(200)
	_, _ = io.WriteString(w, "ok\n")
}

func handleSSE(w http.ResponseWriter, r *http.Request) {
	n, _ := strconv.Atoi(r.URL.Query().Get("n"))
	if n <= 0 {
		n = 5
	}
	interval, _ := strconv.Atoi(r.URL.Query().Get("interval"))
	if interval <= 0 {
		interval = 200
	}
	fl, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming unsupported", 500)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(200)
	fl.Flush()
	for i := 1; i <= n; i++ {
		fmt.Fprintf(w, "id: %d\ndata: {\"n\":%d,\"instance\":\"%s\",\"t\":%d}\n\n", i, i, instance, time.Now().UnixMilli())
		fl.Flush()
		if i < n {
			select {
			case <-time.After(time.Duration(interval) * time.Millisecond):
			case <-r.Context().Done():
				return
			}
		}
	}
}

// ---------------------------------------------------------------------------------------------- websocket (RFC 6455, echo)

func handleWS(w http.ResponseWriter, r *http.Request) {
	if !strings.EqualFold(r.Header.Get("Upgrade"), "websocket") {
		http.Error(w, "expected a WebSocket upgrade (Upgrade: websocket)\n", 426)
		return
	}
	key := r.Header.Get("Sec-WebSocket-Key")
	hj, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "hijack unsupported (HTTP/2?)", 500)
		return
	}
	h := sha1.New()
	h.Write([]byte(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))
	accept := base64.StdEncoding.EncodeToString(h.Sum(nil))
	conn, rw, err := hj.Hijack()
	if err != nil {
		return
	}
	defer conn.Close()
	fmt.Fprintf(rw, "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\nX-Instance: %s\r\n\r\n", accept, instance)
	_ = rw.Flush()
	for {
		_ = conn.SetReadDeadline(time.Now().Add(120 * time.Second))
		op, payload, err := wsRead(rw)
		if err != nil {
			return
		}
		switch op {
		case 0x1, 0x2: // text / binary -> echo
			wsMsgs.Add(1)
			if err := wsWrite(rw, op, payload); err != nil {
				return
			}
		case 0x9: // ping -> pong
			if err := wsWrite(rw, 0xA, payload); err != nil {
				return
			}
		case 0x8: // close
			_ = wsWrite(rw, 0x8, payload)
			return
		}
	}
}

func wsRead(r io.Reader) (byte, []byte, error) {
	var hdr [2]byte
	if _, err := io.ReadFull(r, hdr[:]); err != nil {
		return 0, nil, err
	}
	op := hdr[0] & 0x0f
	masked := hdr[1]&0x80 != 0
	n := uint64(hdr[1] & 0x7f)
	switch n {
	case 126:
		var b [2]byte
		if _, err := io.ReadFull(r, b[:]); err != nil {
			return 0, nil, err
		}
		n = uint64(binary.BigEndian.Uint16(b[:]))
	case 127:
		var b [8]byte
		if _, err := io.ReadFull(r, b[:]); err != nil {
			return 0, nil, err
		}
		n = binary.BigEndian.Uint64(b[:])
	}
	if n > 16<<20 {
		return 0, nil, errors.New("frame too large")
	}
	var mask [4]byte
	if masked {
		if _, err := io.ReadFull(r, mask[:]); err != nil {
			return 0, nil, err
		}
	}
	payload := make([]byte, n)
	if _, err := io.ReadFull(r, payload); err != nil {
		return 0, nil, err
	}
	if masked {
		for i := range payload {
			payload[i] ^= mask[i%4]
		}
	}
	return op, payload, nil
}

func wsWrite(w *bufio.ReadWriter, op byte, payload []byte) error {
	hdr := []byte{0x80 | op}
	n := len(payload)
	switch {
	case n < 126:
		hdr = append(hdr, byte(n))
	case n < 65536:
		hdr = append(hdr, 126, byte(n>>8), byte(n))
	default:
		hdr = append(hdr, 127)
		var b [8]byte
		binary.BigEndian.PutUint64(b[:], uint64(n))
		hdr = append(hdr, b[:]...)
	}
	if _, err := w.Write(hdr); err != nil {
		return err
	}
	if _, err := w.Write(payload); err != nil {
		return err
	}
	return w.Flush()
}

