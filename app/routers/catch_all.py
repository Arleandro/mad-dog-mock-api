from __future__ import annotations
import json
from typing import Optional
from fastapi import Depends, APIRouter, HTTPException, Request, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from ..storage.memory import InMemoryStore
from ..di import get_store
from ..models import Mock, MockResponse
from ..utils.jsonpath import jsonpath_get
from ..core.jwt_validator import validate_jwt

router = APIRouter()

def _contains(val, needle) -> bool:
    try:
        if isinstance(val, list):
            return needle in val
        if isinstance(val, dict):
            return str(needle) in val.values() or needle in val.keys()
        return str(needle) in str(val)
    except Exception:
        return False

def eval_predicate(pred, *, headers, query, path_params, body, jwt_ctx) -> bool:
    v = None
    if pred.source == "header":
        v = headers.get((pred.key or "").lower())
    elif pred.source == "query":
        v = query.get(pred.key or "")
    elif pred.source == "path":
        v = path_params.get(pred.key or "")
    elif pred.source == "body":
        if pred.jsonpath:
            v = jsonpath_get(pred.jsonpath, body)
        elif pred.key and isinstance(body, dict):
            v = body.get(pred.key)
    elif pred.source == "jwt_header":
        v = (jwt_ctx.get("header") or {}).get(pred.key or "")
    elif pred.source == "jwt_payload":
        if pred.jsonpath:
            v = jsonpath_get(pred.jsonpath, jwt_ctx.get("payload"))
        else:
            print('------------------payload')
            print(jwt_ctx.get("payload"))
            print('------------------pred.key')
            print(pred.key)
            print('------------------pred.value')
            v = (jwt_ctx.get("payload") or {}).get(pred.key or "")
            print(v)
    if pred.op == "equals": return v == pred.value
    if pred.op == "regex":
        import re
        try: return bool(re.search(str(pred.value or ""), str(v or "")))
        except Exception: return False
    if pred.op == "contains": return _contains(v, pred.value)
    if pred.op == "in":
        if pred.values is None: return False
        return str(v) in {str(x) for x in pred.values}
    return False

def pick_response_for_mock(m: Mock, *, headers, query, path_params, body, jwt_ctx) -> MockResponse:
    for v in (m.variants or []):
        if all(eval_predicate(p, headers=headers, query=query, path_params=path_params, body=body, jwt_ctx=jwt_ctx) for p in v.when):
            return v.response
    return m.response

async def maybe_validate_jwt(scenario, *, headers, cookies):
    jwt_ctx = {"header": {}, "payload": {}}
    if (scenario.jwt_location or "none") == "none":
        return jwt_ctx, None
    token = None
    if scenario.jwt_location == "header":
        name = (scenario.jwt_header_name or "Authorization").lower()
        raw = headers.get(name)
        if raw and (scenario.jwt_is_bearer if scenario.jwt_is_bearer is not None else True):
            parts = (raw or "").split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
            else:
                token = raw
        else:
            token = raw
    elif scenario.jwt_location == "cookie":
        token = cookies.get(scenario.jwt_cookie_name or "")
    if (scenario.jwt_location in ("header","cookie")) and not token:
        return jwt_ctx, ("missing", "JWT token not found in request")
    if token:
        try:
            if not scenario.jwt_issuer_url:
                return jwt_ctx, ("config", "JWT issuer URL not configured for scenario")
            jwt_ctx = await validate_jwt(token, scenario.jwt_issuer_url)
            return jwt_ctx, None
        except Exception as e:
            msg = str(e)
            if "ConnectError" in msg or "ReadTimeout" in msg or "HTTP" in msg.lower():
                return jwt_ctx, ("integration", f"Error contacting JWT Issuer: {msg}")
            return jwt_ctx, ("validation", f"JWT validation error: {msg}")
    return jwt_ctx, None

@router.api_route("/{full_path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def catch_all(request: Request, full_path: str, body_raw: Optional[str] = Body(None), store: InMemoryStore = Depends(get_store)):
    path = "/" + full_path; method = request.method.upper()
    query = {k: v for k, v in request.query_params.items()}
    headers = {k.lower(): v for k, v in request.headers.items()}
    cookies = request.cookies
    parsed_body = None
    if body_raw:
        ctype = headers.get("content-type","")
        if "application/json" in ctype:
            try: parsed_body = json.loads(body_raw)
            except json.JSONDecodeError: parsed_body = body_raw
        else: parsed_body = body_raw
    match = await store.find_match(path, method, query, headers, parsed_body)
    if not match: raise HTTPException(status_code=404, detail=f"No mock matched {method} {path}")
    mock, path_params, scenario = match
    jwt_ctx, jwt_err = await maybe_validate_jwt(scenario, headers=headers, cookies=cookies)
    if jwt_err:
        kind, message = jwt_err
        status = 401 if kind in ("missing","validation","config") else 502
        raise HTTPException(status_code=status, detail=message)
    chosen = pick_response_for_mock(mock, headers=headers, query=query, path_params=path_params, body=parsed_body, jwt_ctx=jwt_ctx)
    status = chosen.status_code; resp_headers = chosen.headers or {}; media_type = chosen.media_type or "application/json"; body_obj = chosen.body
    if media_type.startswith("application/json"):
        return JSONResponse(content=body_obj, status_code=status, headers=resp_headers, media_type=media_type)
    else:
        text = body_obj if isinstance(body_obj, str) else json.dumps(body_obj, ensure_ascii=False)
        return PlainTextResponse(content=text, status_code=status, headers=resp_headers, media_type=media_type)
