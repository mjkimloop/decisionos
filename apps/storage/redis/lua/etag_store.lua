-- ETag Store - Atomic operations with Lua script
-- KEYS[1]=hashKey  ARGV: op, now, ttl, etag, val_json, match, base_etag
local k=KEYS[1]; local op=ARGV[1]; local now=ARGV[2]; local ttl=tonumber(ARGV[3])
local new_etag=ARGV[4]; local val=ARGV[5]; local match=ARGV[6]; local base=ARGV[7]

if op=="PUT" then
  redis.call("HSET",k,"etag",new_etag,"ts",now,"val",val,"ttl",ttl)
  redis.call("PEXPIRE",k,ttl)
  return "OK"
elseif op=="CAS" then
  local cur=redis.call("HGET",k,"etag")
  if not cur then return "MISSING" end
  if cur~=match then return "NOMATCH" end
  redis.call("HSET",k,"etag",new_etag,"ts",now,"val",val,"ttl",ttl)
  redis.call("PEXPIRE",k,ttl)
  return "OK"
elseif op=="DELTA" then
  local cur=redis.call("HGET",k,"etag")
  if not cur then return "MISSING" end
  if cur~=base then return "NOMATCH" end
  -- 단순 치환(증분 계산은 Python에서 val_json에 반영해 전달)
  redis.call("HSET",k,"etag",new_etag,"ts",now,"val",val,"ttl",ttl)
  redis.call("PEXPIRE",k,ttl)
  return "OK"
elseif op=="GET" then
  local h=redis.call("HGETALL",k)
  return h
end
return "ERR"
