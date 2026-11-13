import hashlib
import json
import logging
from contextlib import contextmanager
import os
import secrets
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

DB = os.getenv("LOCALAI_DB", "/var/lib/localai/state/gateway.sqlite3")
UPSTREAM = os.getenv("LOCALAI_UPSTREAM", "http://127.0.0.1:8081")
MODEL = os.getenv("LOCALAI_MODEL", "local-qwen3-4b")
MAX_BYTES = int(os.getenv("LOCALAI_MAX_BYTES", "65536"))
TIMEOUT = float(os.getenv("LOCALAI_TIMEOUT", "120"))
SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 owner_id TEXT NOT NULL, key_hash TEXT NOT NULL UNIQUE,
 scopes TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
 expires_at TEXT, daily_limit INTEGER NOT NULL DEFAULT 100,
 created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS usage_daily (
 key_id INTEGER NOT NULL, day_utc TEXT NOT NULL,
 requests INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(key_id, day_utc));
"""

logger = logging.getLogger("localai.gateway")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
app = FastAPI(title="Local AI Gateway", version="0.1")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def db_open():
    conn = sqlite3.connect(DB, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    with db_open() as conn:
        conn.executescript(SCHEMA)


@app.on_event("startup")
def startup() -> None:
    init_db()


def event(kind: str, request_id: str, **meta: object) -> None:
    # Never log prompts, responses, or authentication secrets.
    logger.info(json.dumps({
        "time": utc_now(), "event": kind,
        "request_id": request_id, **meta
    }, ensure_ascii=False, separators=(",", ":")))


def reject(status: int, code: str) -> None:
    raise HTTPException(status_code=status, detail={"code": code})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "error": {"code": "invalid_schema"}
    })


def authorize(request: Request, scope: str) -> sqlite3.Row:
    raw = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not raw.startswith(prefix):
        reject(401, "missing_credentials")
    token = raw[len(prefix):]
    if len(token) > 256 or len(token) < 32:
        reject(401, "invalid_credentials")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with db_open() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND enabled = 1",
            (digest,)
        ).fetchone()
    if row is None:
        reject(401, "invalid_credentials")
    if row["expires_at"] and row["expires_at"] <= utc_now():
        reject(401, "expired_credentials")
    if scope not in row["scopes"].split(","):
        reject(403, "insufficient_scope")
    return row


def charge_quota(key_id: int, limit: int) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    with db_open() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            current = conn.execute(
                "SELECT requests FROM usage_daily WHERE key_id=? AND day_utc=?",
                (key_id, today)
            ).fetchone()
            count = current[0] if current else 0
            if count >= limit:
                conn.execute("ROLLBACK")
                reject(429, "daily_quota_exceeded")
            conn.execute("""
                INSERT INTO usage_daily(key_id,day_utc,requests)
                VALUES(?,?,1)
                ON CONFLICT(key_id,day_utc)
                DO UPDATE SET requests=requests+1
            """, (key_id, today))
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=16000)
    model_config = {"extra": "forbid"}


class ChatBody(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    messages: list[Message] = Field(min_length=1, max_length=40)
    max_tokens: int = Field(default=256, ge=1, le=2048)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    stream: bool = False
    model_config = {"extra": "forbid"}


@app.get("/health/live")
def live():
    return {"status": "alive"}


@app.get("/health/ready")
async def ready():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"{UPSTREAM}/v1/models")
            res.raise_for_status()
        return {"status": "ready"}
    except httpx.HTTPError:
        reject(503, "upstream_unavailable")


@app.get("/v1/models")
def models(request: Request):
    authorize(request, "models:read")
    return {"object": "list", "data": [
        {"id": MODEL, "object": "model", "owned_by": "local"}
    ]}


@app.post("/v1/chat/completions")
async def chat(request: Request):
    request_id = secrets.token_hex(12)
    started = time.monotonic()
    key_id = None
    status = 500
    try:
        row = authorize(request, "chat:write")
        key_id = int(row["id"])
        content_type = request.headers.get("content-type", "").split(";")[0]
        if content_type != "application/json":
            reject(415, "unsupported_media_type")
        if int(request.headers.get("content-length", "0")) > MAX_BYTES:
            reject(413, "body_too_large")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                reject(413, "body_too_large")
        try:
            body = ChatBody.model_validate_json(bytes(raw))
        except Exception:
            reject(400, "invalid_request")
        if body.model != MODEL:
            reject(400, "model_not_allowed")
        if body.stream:
            reject(400, "stream_not_supported")
        charge_quota(key_id, int(row["daily_limit"]))
        payload = body.model_dump()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                upstream = await client.post(
                    f"{UPSTREAM}/v1/chat/completions", json=payload
                )
                upstream.raise_for_status()
                result = upstream.json()
        except httpx.TimeoutException:
            reject(503, "upstream_timeout")
        except (httpx.HTTPError, ValueError):
            reject(502, "upstream_error")
        status = 200
        return JSONResponse(status_code=200, content=result,
                            headers={"X-Request-Id": request_id})
    except HTTPException as exc:
        status = exc.status_code
        raise
    finally:
        event("inference_request", request_id,
              key_id=key_id, status=status, model=MODEL,
              latency_ms=round((time.monotonic()-started)*1000))