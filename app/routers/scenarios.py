from __future__ import annotations
from typing import Any, Dict, List
from fastapi import Depends, APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from ..storage.memory import InMemoryStore
from ..di import get_store
from ..models import Scenario, ScenarioCreate, ScenarioUpdate
from ..core.openapi_builder import build_scenario_openapi
from ..core.config import APP_TITLE, APP_VERSION

router = APIRouter(tags=["scenarios"])

def swagger_urls_for(basepath: str) -> Dict[str,str]:
    return {"openapi_url": f"/scenarios{basepath}/openapi.json", "docs_url": f"/scenarios{basepath}/docs"}

@router.get("/api/scenarios")
async def list_scenarios(store: InMemoryStore = Depends(get_store)) -> List[Dict[str, Any]]:
    items = await store.list_scenarios()
    return [{**s.model_dump(), **swagger_urls_for(s.basepath)} for s in items]

@router.get("/api/scenarios/{basepath:path}", response_model=Scenario)
async def get_scenario(basepath: str, store: InMemoryStore = Depends(get_store)) -> Scenario:
    try: return await store.get_scenario(basepath)
    except KeyError: raise HTTPException(status_code=404, detail="Scenario not found")

@router.post("/api/scenarios", response_model=Scenario, status_code=201)
async def create_scenario(sc: ScenarioCreate, store: InMemoryStore = Depends(get_store)) -> Scenario:
    try: return await store.create_scenario(sc)
    except ValueError as e: raise HTTPException(status_code=409, detail=str(e))

@router.put("/api/scenarios/{basepath:path}", response_model=Scenario)
async def update_scenario(basepath: str, patch: ScenarioUpdate, store: InMemoryStore = Depends(get_store)) -> Scenario:
    try: return await store.update_scenario(basepath, patch)
    except KeyError: raise HTTPException(status_code=404, detail="Scenario not found")
    except ValueError as e: raise HTTPException(status_code=409, detail=str(e))

@router.delete("/api/scenarios/{basepath:path}", status_code=204)
async def delete_scenario(basepath: str, store: InMemoryStore = Depends(get_store)):
    await store.delete_scenario(basepath); return {}

SWAGGER_UI = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Scenario - Swagger UI</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" /></head>
<body><div id="swagger-ui"></div><script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
<script>window.ui=SwaggerUIBundle({url:'%OPENAPI%',dom_id:'#swagger-ui'});</script></body></html>"""

@router.get("/scenarios{basepath:path}/openapi.json")
async def scenario_openapi(basepath: str, store: InMemoryStore = Depends(get_store)) -> Dict[str, Any]:
    try: s = await store.get_scenario(basepath)
    except KeyError: raise HTTPException(status_code=404, detail="Scenario not found")
    mocks = await store.list_mocks()
    return build_scenario_openapi(s, mocks, APP_TITLE, APP_VERSION, "/docs/guide.html")

@router.get("/scenarios{basepath:path}/docs", response_class=HTMLResponse)
async def scenario_docs(basepath: str):
    return HTMLResponse(SWAGGER_UI.replace("%OPENAPI%", f"/scenarios{basepath}/openapi.json"))
