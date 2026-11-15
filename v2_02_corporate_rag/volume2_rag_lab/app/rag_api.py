"""Single-tenant API for internal use behind an authenticated reverse proxy."""
from __future__ import annotations
import hmac
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from rag_core import (RagStore, RagConfig, answer, read_secret,
                      InputError, UpstreamError, MAX_QUESTION_CHARS)


def create_app(config: RagConfig | None = None, generate=None) -> FastAPI:
    app = FastAPI(title='Local AI RAG laboratory', docs_url=None,
                  redoc_url=None, openapi_url=None)
    resolved_config = config or RagConfig.from_env()
    expected_key = read_secret(resolved_config.app_secret_file)

    @app.get('/healthz')
    def healthz():
        return {'status': 'ok'}

    @app.post('/v1/rag/answers')
    async def rag_answers(req: Request):
        header = req.headers.get('authorization','')
        supplied = header[7:] if header.startswith('Bearer ') else ''
        if not supplied or not hmac.compare_digest(supplied, expected_key):
            raise HTTPException(401, 'Unauthorized', headers={'WWW-Authenticate':'Bearer'})
        if req.headers.get('content-type','').split(';')[0].lower() != 'application/json':
            raise HTTPException(415, 'JSON content type required')
        data = bytearray()
        async for block in req.stream():
            data.extend(block)
            if len(data) > 8192:
                raise HTTPException(413, 'Request too large')
        try:
            obj = json.loads(bytes(data))
            if not isinstance(obj, dict) or set(obj) != {'question'}:
                raise ValueError('Unexpected request fields')
            question = obj['question']
            if not isinstance(question, str) or not (2 <= len(question) <= MAX_QUESTION_CHARS):
                raise ValueError('Question length invalid')
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, 'Invalid request body')
        store = RagStore(resolved_config.db_path)
        try:
            if generate is None:
                result = answer(store, question, resolved_config)
            else:
                result = answer(store, question, resolved_config, generate=generate)
        except InputError:
            raise HTTPException(400, 'Question cannot be searched')
        except UpstreamError:
            raise HTTPException(503, 'Model service unavailable')
        finally:
            store.close()
        return JSONResponse(result, headers={'Cache-Control':'no-store'})
    return app


# Use uvicorn's --factory option; missing configuration fails startup.
