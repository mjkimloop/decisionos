-- Replay Guard - Atomic nonce check with clock skew validation
-- KEYS[1]=nonceKey  ARGV: now_ms, skew_min_ms, skew_max_ms, ttl_ms
local k=KEYS[1]; local now=tonumber(ARGV[1])
local skewMin=tonumber(ARGV[2]); local skewMax=tonumber(ARGV[3]); local ttl=tonumber(ARGV[4])

if now<skewMin or now>skewMax then
  return "REJECT_CLOCKSKEW"
end

local ok=redis.call("SET",k,now,"NX","PX",ttl)
if ok then
  return "ALLOW"
else
  return "REJECT_EXIST"
end
