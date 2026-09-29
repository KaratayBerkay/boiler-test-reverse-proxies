# remap rules, one per line: <from-host> <from-path> <to-url> [remap params...]
# gen.py expands every http rule for the ports clients use (none/80/8080/18080) and https for 8443/18443,
# because ATS matches the port of the request URL (Host header) against the from-URL.
a.lab            /            http://app1:8080/          @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/route-a.conf
b.lab            /            http://b1:8080/            @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/route-b.conf
weighted.lab     /            http://app1:8080/          @strategy=weighted
leastconn.lab    /            http://app1:8080/          @strategy=app
hash.lab         /            http://app1:8080/          @strategy=app
sticky.lab       /            http://app1:8080/          @strategy=app
retry.lab        /            http://app1:8080/          @strategy=retry
cb.lab           /            http://app1:8080/          @strategy=cb
health.lab       /            http://app1:8080/          @strategy=app
canary.lab       /            http://app1:8080/          @strategy=canary
mirror.lab       /            http://app1:8080/          @strategy=app @plugin=multiplexer.so @pparam=shadow:8080
pp.lab           /            http://app1:8080/          @strategy=app
h2.lab           /            http://app1:8080/          @strategy=app
tls.lab          /            https://app1:8443/
auth.lab         /            http://app1:8080/          @strategy=app
jwt.lab          /            http://app1:8080/          @strategy=app
mtls.lab         /            http://app1:8080/          @strategy=app
acme.lab         /            http://app1:8080/          @strategy=app
app.lab          /api/        http://app1:8080/          @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/api.conf
app.lab          /old/        http://app1:8080/new/      @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/rewritten.conf
app.lab          /limited     http://app1:8080/limited   @strategy=app @plugin=rate_limit.so @pparam=--limit=3 @pparam=--queue=0 @pparam=--error=429
app.lab          /conn-limited http://app1:8080/delay/1000 @strategy=app @plugin=rate_limit.so @pparam=--limit=3 @pparam=--queue=0 @pparam=--error=429
app.lab          /allowed     http://app1:8080/allowed   @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/allowed.conf
app.lab          /denied      http://app1:8080/denied    @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/denied.conf
app.lab          /basic       http://app1:8080/basic     @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/basic.conf
app.lab          /upload      http://app1:8080/upload    @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/upload.conf
app.lab          /timeout     http://app1:8080/delay/5000 @plugin=conf_remap.so @pparam=proxy.config.http.transaction_no_activity_timeout_out=2 @pparam=proxy.config.http.connect_attempts_rr_retries=0 @pparam=proxy.config.http.connect_attempts_max_retries=0
app.lab          /fault       http://app1:8080/fault     @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/fault.conf
app.lab          /bw          http://app1:8080/bin/1048576 @strategy=app
app.lab          /static/index.html http://app1:8080/ @plugin=statichit.so @pparam=--file-path=/static/index.html @pparam=--mime-type=text/html @pparam=--disable-exact
app.lab          /error-page  http://app1:8080/status/503 @strategy=app
app.lab          /cors        http://app1:8080/cors      @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/cors.conf
app.lab          /secure      http://app1:8080/secure    @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/secure.conf
app.lab          /compressible http://app1:8080/size/65536 @strategy=app
app.lab          /grpc.health.v1.Health/ http://app1:9090/grpc.health.v1.Health/
app.lab          /            http://app1:8080/          @strategy=app @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/app-root.conf
redirect.lab     /            https://redirect.lab/      @redirect
app.lab          /redirect-me http://app1:8080/redirect-me @plugin=header_rewrite.so @pparam=/etc/trafficserver/hdr/redirect.conf
shadow           /            http://shadow:8080/        @mirror-target
