# OpenResty (nginx + LuaJIT) with the Lua libraries the lab uses, installed through opm at build time:
#   lua-resty-jwt (JWT), nginx-lua-prometheus (metrics),
#   lua-resty-acme (+ lua-resty-http, lua-resty-openssl: ACME client in Lua), lua-resty-limit-traffic is bundled.
FROM openresty/openresty:1.27.1.2-alpine-fat
RUN opm get SkyLothar/lua-resty-jwt knyar/nginx-lua-prometheus fffonion/lua-resty-acme ledgetech/lua-resty-http \
 && apk add --no-cache curl
