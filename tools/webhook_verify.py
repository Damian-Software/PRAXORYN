"""HMAC verification example with timestamp and max body size."""
import hashlib
import hmac
import time


def sign(body: bytes, timestamp: int, secret: bytes) -> str:
    payload=str(timestamp).encode('ascii')+b'.'+body
    return hmac.new(secret,payload,hashlib.sha256).hexdigest()


def verify(body: bytes, timestamp: int, signature: str, secret: bytes, now=None):
    now=int(time.time()) if now is None else now
    if len(body)>65536:return False
    if abs(now-timestamp)>300:return False
    expected=sign(body,timestamp,secret)
    return hmac.compare_digest(expected,signature)
