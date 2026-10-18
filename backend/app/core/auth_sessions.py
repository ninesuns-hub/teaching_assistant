"""Server-side login sessions: reads never renew the idle deadline."""
import json
import time
import uuid

from agent_core.config.settings import settings
from app.core.redis_client import redis_client

PREFIX = "auth_session:v1:"


def create_session(email: str) -> dict:
    now = int(time.time())
    absolute = now + min(480, settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    idle = min(absolute, now + settings.AUTH_IDLE_TIMEOUT_MINUTES * 60)
    session = {"sid": str(uuid.uuid4()), "email": email,
               "expires_at": absolute, "idle_expires_at": idle}
    redis_client.client.setex(PREFIX + session["sid"], idle - now, json.dumps(session))
    return session


def read_session(sid: str, email: str) -> dict:
    raw = redis_client.client.get(PREFIX + sid) if sid else None
    session = json.loads(raw) if raw else None
    now = time.time()
    if (not session or session.get("email") != email
            or min(session["expires_at"], session["idle_expires_at"]) <= now):
        raise ValueError("登录已过期，请重新登录")
    return session


def touch_session(sid: str) -> dict:
    # Atomic renewal prevents a concurrent logout from resurrecting a session.
    raw = redis_client.client.eval("""
local raw = redis.call('GET', KEYS[1])
if not raw then return false end
local session = cjson.decode(raw)
local now = tonumber(ARGV[1])
if session.expires_at <= now or session.idle_expires_at <= now then return false end
session.idle_expires_at = math.min(session.expires_at, now + tonumber(ARGV[2]))
local result = cjson.encode(session)
redis.call('SET', KEYS[1], result, 'EX', session.idle_expires_at - now)
return result
""", 1, PREFIX + sid, int(time.time()), settings.AUTH_IDLE_TIMEOUT_MINUTES * 60)
    if not raw:
        raise ValueError("登录已过期，请重新登录")
    return json.loads(raw)


def delete_session(sid: str) -> None:
    redis_client.client.delete(PREFIX + sid)
