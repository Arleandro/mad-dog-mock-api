from __future__ import annotations
from typing import Any, Dict, List
from ..models import Mock, Scenario, ensure_leading_slash

def build_scenario_openapi(scenario: Scenario, mocks: List[Mock], app_title: str, app_version: str, guide_url: str) -> Dict[str, Any]:
    paths: Dict[str, Any] = {}
    tags: Dict[str, Dict[str, str]] = {}
    import re as _re

    for m in mocks:
        if not m.enabled or m.scenario_basepath != scenario.basepath: continue
        full = ensure_leading_slash(scenario.basepath.rstrip("/") + "/" + m.request.uri.lstrip("/"))
        item = paths.setdefault(full, {})
        params = []
        for name in _re.findall(r"\{([a-zA-Z0-9_]+)\}", m.request.uri):
            params.append({"name": name, "in": "path", "required": False, "schema": {"type":"string"}, "description": f"Path param: {name}"})
        for p in (m.request.params or []):
            params.append({"name": p.name, "in": p.in_, "required": False, "schema": {"type": p.schema_type}, "description": p.description or "", "example": p.example})
        req_body = None
        if m.request.example_body is not None or m.request.content_type:
            req_body = {"required": False, "content": {(m.request.content_type or "application/json"): {"example": m.request.example_body}}}
        responses = {str(m.response.status_code): {"description": m.response.description or "Mocked response", "content": {(m.response.media_type or "application/json"): {"example": m.response.body}}}}
        if m.variants:
            for v in m.variants:
                code = str(v.response.status_code)
                if code not in responses:
                    responses[code] = {"description": v.response.description or (v.description or "Variant response"), "content": {(v.response.media_type or "application/json"): {"example": v.response.body}}}
        op = {"summary": m.name or f"Mock {m.id}", "description": (m.description or "") + f"\n\nMock-ID: {m.id}", "tags": m.tags or [], "parameters": params, "responses": responses}
        if req_body: op["requestBody"] = req_body
        item[m.request.method.lower()] = op
        for t in (m.tags or []): tags.setdefault(t, {"name": t, "description": f"Grupo: {t}"})

    info_desc = (scenario.description or "")
    if guide_url: info_desc += f"\n\n**Documentação:** [Guia (Markdown)]({guide_url})"
    return {"openapi": "3.0.3", "info": {"title": f"{app_title} — Cenário {scenario.basepath}", "version": app_version, "description": info_desc}, "tags": list(tags.values()), "paths": paths or {}, "components": {}}
