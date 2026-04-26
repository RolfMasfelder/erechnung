-- JWT Validator for API Gateway (Defense-in-Depth)
--
-- Validates JWT tokens at the nginx perimeter BEFORE requests reach Django.
-- Invalid/expired tokens are rejected in <1ms without touching the backend.
-- Django still performs its own full JWT validation (double-check).
--
-- Security benefits:
--   1. DDoS protection: garbage tokens never reach Django
--   2. Independent second validation layer
--   3. Reduced backend load from unauthenticated requests
--
-- Requires: OpenResty + lua-resty-jwt

local jwt = require("resty.jwt")
local cjson = require("cjson.safe")

-- Read JWT secret from shared dict (set in init_by_lua_block)
local jwt_secret = ngx.shared.jwt_config:get("secret")

if not jwt_secret then
    -- No secret configured → pass through (graceful degradation)
    ngx.log(ngx.WARN, "JWT_SIGNING_KEY not configured, skipping gateway JWT validation")
    return
end

-- Skip validation for OPTIONS (CORS preflight)
if ngx.req.get_method() == "OPTIONS" then
    return
end

-- Extract Authorization header
local auth_header = ngx.var.http_authorization
if not auth_header then
    ngx.status = 401
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({
        detail = "Authentication credentials were not provided.",
        gateway = true,
    }))
    return ngx.exit(401)
end

-- Validate "Bearer <token>" format
local token = auth_header:match("^Bearer%s+(.+)$")
if not token then
    ngx.status = 401
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({
        detail = "Invalid authorization header format. Expected: Bearer <token>",
        gateway = true,
    }))
    return ngx.exit(401)
end

-- Verify JWT signature and claims
local jwt_obj = jwt:verify(jwt_secret, token)

if not jwt_obj.verified then
    local reason = jwt_obj.reason or "Token verification failed"

    -- Log for monitoring (no sensitive data)
    ngx.log(ngx.WARN, "JWT rejected at gateway: ", reason,
        " remote_addr=", ngx.var.remote_addr)

    -- Determine appropriate error message
    local detail = "Token is invalid or expired."
    if reason:find("expired") then
        detail = "Token has expired."
    end

    ngx.status = 401
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({
        detail = detail,
        code = "token_not_valid",
        gateway = true,
    }))
    return ngx.exit(401)
end

-- Token is valid — pass validated user info as headers to Django
-- Django will still do its own full validation (defense-in-depth)
local payload = jwt_obj.payload
if payload and payload.user_id then
    ngx.req.set_header("X-Gateway-User-Id", tostring(payload.user_id))
end
ngx.req.set_header("X-Gateway-JWT-Verified", "true")
