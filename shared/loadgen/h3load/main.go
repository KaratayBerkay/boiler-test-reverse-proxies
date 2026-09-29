// h3load: a small HTTP/3 (QUIC) load generator, because none of the usual tools (wrk, oha, k6, h2load as packaged)
// speak HTTP/3. N QUIC connections × M concurrent streams each, closed-loop, for a fixed duration; JSON summary.
//
//	h3load -url https://proxy:8443/small -conns 8 -streams 8 -d 15s -insecure -host app.lab
package main

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"github.com/quic-go/quic-go"
	"github.com/quic-go/quic-go/http3"
)

type result struct {
	Tool         string             `json:"tool"`
	URL          string             `json:"url"`
	Conns        int                `json:"conns"`
	Streams      int                `json:"streams_per_conn"`
	DurationS    float64            `json:"duration_s"`
	Requests     int64              `json:"requests"`
	RPS          float64            `json:"rps"`
	Status       map[string]int64   `json:"status"`
	Errors       int64              `json:"errors"`
	ErrorSamples []string           `json:"error_samples"`
	Bytes        int64              `json:"bytes"`
	LatencyMs    map[string]float64 `json:"latency_ms"`
	Protocol     string             `json:"protocol"`
}

func main() {
	url := flag.String("url", "https://127.0.0.1:8443/", "target URL (https)")
	conns := flag.Int("conns", 8, "QUIC connections")
	streams := flag.Int("streams", 8, "concurrent requests per connection")
	dur := flag.Duration("d", 10*time.Second, "test duration")
	insecure := flag.Bool("insecure", true, "skip TLS verification")
	host := flag.String("host", "", "Host header / SNI override")
	flag.Parse()

	var reqs, errs, bytesTotal atomic.Int64
	var mu sync.Mutex
	lat := make([]float64, 0, 1<<20)
	status := map[string]int64{}
	samples := []string{}
	proto := ""

	ctx, cancel := context.WithTimeout(context.Background(), *dur)
	defer cancel()
	var wg sync.WaitGroup
	start := time.Now()
	for c := 0; c < *conns; c++ {
		tr := &http3.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: *insecure, NextProtos: []string{"h3"}, ServerName: *host},
			QUICConfig:      &quic.Config{MaxIdleTimeout: 30 * time.Second, KeepAlivePeriod: 10 * time.Second},
		}
		client := &http.Client{Transport: tr}
		for s := 0; s < *streams; s++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for ctx.Err() == nil {
					req, _ := http.NewRequestWithContext(ctx, "GET", *url, nil)
					if *host != "" {
						req.Host = *host
					}
					t0 := time.Now()
					resp, err := client.Do(req)
					if err != nil {
						if ctx.Err() != nil {
							return
						}
						errs.Add(1)
						mu.Lock()
						if len(samples) < 5 {
							samples = append(samples, err.Error())
						}
						mu.Unlock()
						time.Sleep(10 * time.Millisecond)
						continue
					}
					n, _ := io.Copy(io.Discard, resp.Body)
					resp.Body.Close()
					ms := float64(time.Since(t0).Microseconds()) / 1000
					reqs.Add(1)
					bytesTotal.Add(n)
					mu.Lock()
					lat = append(lat, ms)
					status[fmt.Sprint(resp.StatusCode)]++
					if proto == "" {
						proto = resp.Proto
					}
					mu.Unlock()
				}
			}()
		}
		defer tr.Close()
	}
	wg.Wait()
	el := time.Since(start).Seconds()
	sort.Float64s(lat)
	pct := func(q float64) float64 {
		if len(lat) == 0 {
			return 0
		}
		i := int(float64(len(lat)-1) * q)
		return lat[i]
	}
	mean := 0.0
	for _, v := range lat {
		mean += v
	}
	if len(lat) > 0 {
		mean /= float64(len(lat))
	}
	r := result{Tool: "h3load", URL: *url, Conns: *conns, Streams: *streams, DurationS: el, Requests: reqs.Load(), RPS: float64(reqs.Load()) / el,
		Status: status, Errors: errs.Load(), ErrorSamples: samples, Bytes: bytesTotal.Load(), Protocol: proto,
		LatencyMs: map[string]float64{"mean": mean, "p50": pct(0.5), "p90": pct(0.9), "p99": pct(0.99), "max": pct(1.0)}}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", " ")
	_ = enc.Encode(r)
}
