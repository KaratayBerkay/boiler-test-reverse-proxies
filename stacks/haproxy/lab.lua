-- pxlab HAProxy Lua: forward authentication. HAProxy has no built-in "ask an external service first" action, so the
-- Lua action calls the auth service with the internal HTTP client (core.httpclient, 2.5+), then the config denies
-- or forwards based on txn.auth_ok / txn.auth_user. Runs on the request path, so keep the timeout short.
core.register_action("forward_auth", { "http-req" }, function(txn)
    local hdrs = txn.http:req_get_headers()
    local token = ""
    if hdrs["x-auth-token"] then
        token = hdrs["x-auth-token"][0]
    elseif hdrs["authorization"] then
        token = string.gsub(hdrs["authorization"][0], "^Bearer ", "")
    end
    local client = core.httpclient()
    local res = client:get{
        url = "http://app1:8080/auth",
        headers = { ["x-auth-token"] = { token }, ["x-original-uri"] = { txn.sf:path() or "/" } },
        timeout = 2000,
    }
    if res and res.status == 200 then
        txn:set_var("txn.auth_ok", 1)
        local user = res.headers and res.headers["x-auth-user"] and res.headers["x-auth-user"][0] or ""
        txn:set_var("txn.auth_user", user)
    else
        txn:set_var("txn.auth_ok", 0)
        txn:set_var("txn.auth_user", "")
    end
end, 0)
