# Apache Traffic Server 9.2 from Ubuntu 24.04 packages (there is no official ATS Docker image); experimental plugins included.
FROM ubuntu:24.04
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends trafficserver trafficserver-experimental-plugins curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* && mkdir -p /var/cache/trafficserver /run/trafficserver && chown -R trafficserver:trafficserver /var/cache/trafficserver /run/trafficserver /var/log/trafficserver
USER trafficserver
CMD ["traffic_server"]
