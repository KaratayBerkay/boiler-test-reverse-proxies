# Explanation — Chaos: failover and reload under load

Failover: fortio at 1 000 rps plus a 20 rps probing timeline while backend app2 is stopped at 6 s and started at 14 s. Reload: oha with 64 keep-alive connections for 15 s, the proxy's native reload issued at 5 s.

| proxy | failover: load errors / requests | timeline failed / requests | fail window s | app2 back after s | max latency ms | reload mechanism | reload: load errors / requests | reload timeline failed / requests | reload s | error samples |
|---|---|---|---|---|---|---|---|---|---|---|
**Apache APISIX 3.15**| 0 / 23,994| 0 / 562| 0.0| 3.4| 44.8| file-watch (standalone mode re-reads apisix.yaml when its mtime changes; routes are swapped without restart)| 0 / 166,414| 0 / 330| 0.04|  |
**Apache httpd 2.4**| 0 / 19,946| 0 / 559| 0.0| 2.6| 4,137| signal (graceful restart: SIGUSR1, children finish their requests, new children read the new config)| 48 / 176,743| 1 / 325| 0.34| connection closed before message completed ×48 |
**Apache Traffic Server 9.2**| 0 / 20,848| 0 / 560| 0.0| 0.4| 3,201| cli (traffic_ctl config reload re-reads remap.config / records.config / plugins without restart)| 0 / 422,368| 0 / 330| 0.09|  |
**Caddy 2**| 0 / 23,921| 0 / 574| 0.0| 0.9| 280| api (caddy reload pushes the config through the admin API; zero-downtime, listeners kept)| 0 / 176,221| 0 / 344| 0.23|  |
**Envoy 1.39**| 0 / 18,225| 0 / 559| 0.0| 4.1| 3,019| xds-file-watch (a new rds.yaml version is picked up by the watched directory and swapped in without restart)| 0 / 267,172| 0 / 328| 0.01|  |
**HAProxy 3.4**| 0 / 15,378| 0 / 570| 0.0| 4.3| 3,003| signal (SIGUSR2 to the master → new worker with the new config, listeners handed over via expose-fd, old worker drains)| 0 / 461,888| 0 / 337| 0.23|  |
**Kong Gateway 3.9**| 0 / 23,974| 0 / 562| 0.0| 3.6| 59.0| api (POST /config on the admin API re-applies the declarative file atomically; `kong reload` only HUPs nginx and does NOT re-read it)| 0 / 155,390| 0 / 326| 0.18|  |
**NGINX 1.29**| 0 / 23,441| 0 / 564| 0.0| 6.1| 3,004| signal (SIGHUP — new workers start with the new config, old workers finish their connections)| 52 / 954,396| 0 / 333| 0.18| connection closed before message completed ×1; connection error ×50; operation was canceled ×1 |
**OpenResty 1.27**| 0 / 23,628| 0 / 564| 0.0| 5.5| 3,001| signal (SIGHUP — new workers with the new config + Lua code, old workers drain)| 28 / 765,919| 0 / 357| 0.22| connection closed before message completed ×1; connection error ×27 |
**Pingora (Rust, custom)**| 1 / 18,389| 0 / 574| 0.0| 3.1| 5,005| zero-downtime upgrade (new process started with -u takes the listening sockets over the upgrade socket; the old one gets SIGQUIT and drains)| 37 / 256,776| 0 / 328| 2.09| connection closed before message completed ×10; connection error ×21; operation was canceled ×6 |
**Traefik v3**| 12 / 22,798| 0 / 560| 0.0| 0.7| 3,139| file-watch (the file provider re-applies dynamic config on change; routers/services are swapped without restart)| 0 / 175,328| 0 / 334| 0.01|  |
**Varnish 8 + hitch**| 0 / 18,288| 0 / 563| 0.0| 1.7| 5,003| cli (varnishreload: vcl.load + vcl.use over the management interface; the new VCL takes over instantly, old VCL retires)| 0 / 157,887| 0 / 331| 1.35|  |

