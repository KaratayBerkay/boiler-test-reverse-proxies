# prometheus_varnish_exporter on top of the same Varnish image (varnishstat must match the running varnishd's VSM format)
FROM varnish:8.0
USER root
ADD https://github.com/jonnenauha/prometheus_varnish_exporter/releases/download/1.6.1/prometheus_varnish_exporter-1.6.1.linux-amd64.tar.gz /tmp/exporter.tgz
RUN tar -xzf /tmp/exporter.tgz -C /tmp && mv /tmp/prometheus_varnish_exporter-*/prometheus_varnish_exporter /usr/local/bin/ && rm -rf /tmp/exporter.tgz /tmp/prometheus_varnish_exporter-*
USER varnish
ENTRYPOINT ["/usr/local/bin/prometheus_varnish_exporter"]
