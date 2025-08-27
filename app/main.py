from __future__ import annotations
from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from .core.config import APP_TITLE, APP_VERSION, CORS_ALLOW_ORIGINS
from .storage.memory import InMemoryStore
from .di import store_instance, get_store
from .routers import scenarios as scenarios_router
from .routers import mocks as mocks_router
from .routers import catch_all as catch_all_router

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "Mad Dog Mock — API para criação de mocks HTTP dinâmicos, agrupados por Cenários, "
        "com Swagger por cenário, respostas condicionais (incl. JWT) e CRUD completo.\n\n"
        "**Documentação:** [Guia (Markdown)](/docs/guide.md) | [Guia (HTML)](/docs/guide.html)"
    ),
    docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
)

app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOW_ORIGINS or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

store_instance = InMemoryStore()
app.include_router(scenarios_router.router)
app.dependency_overrides[get_store] = lambda: store_instance
app.dependency_overrides[scenarios_router.InMemoryStore] = lambda: store
app.include_router(mocks_router.router)
app.dependency_overrides[get_store] = lambda: store_instance
app.dependency_overrides[mocks_router.InMemoryStore] = lambda: store

from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path as _Path

# Static docs (guide.md/html)
_BASE_DIR = _Path(__file__).resolve().parent.parent
_DOCS_DIR = _BASE_DIR / "docs"
if _DOCS_DIR.exists():
    app.mount("/docs-site", StaticFiles(directory=str(_DOCS_DIR), html=False), name="docs-site")

@app.get("/docs/guide.html", include_in_schema=False)
async def _serve_docs_html():
    file_path = _DOCS_DIR / "guide.html"
    if not file_path.exists():
        return JSONResponse({"detail": "guide.html não encontrado"}, status_code=404)
    return FileResponse(str(file_path), media_type="text/html")

@app.get("/docs/guide.md", include_in_schema=False)
async def _serve_docs_md():
    file_path = _DOCS_DIR / "guide.md"
    if not file_path.exists():
        return JSONResponse({"detail": "guide.md não encontrado"}, status_code=404)
    return FileResponse(str(file_path), media_type="text/markdown")

@app.get("/help", include_in_schema=False)
async def _help_redirect():
    # simples atalho para abrir a documentação HTML
    if (_DOCS_DIR / "guide.html").exists():
        return RedirectResponse(url="/docs/guide.html")
    return RedirectResponse(url="/docs-site/")

app.include_router(catch_all_router.router)
app.dependency_overrides[get_store] = lambda: store_instance
app.dependency_overrides[catch_all_router.InMemoryStore] = lambda: store

@app.get("/healthz/live", tags=["health"])
async def liveness() -> Dict[str, str]:
    return {"status":"live"}

@app.get("/healthz/ready", tags=["health"])
async def readiness() -> Dict[str, str]:
    return {"status":"ready"}

@app.get("/docs/guide.md", response_class=FileResponse, include_in_schema=False)
async def guide_md():
    return FileResponse("docs/guide.md", media_type="text/markdown")

@app.get("/docs/guide.html", response_class=FileResponse, include_in_schema=False)
async def guide_html():
    return FileResponse("docs/guide.html", media_type="text/html")

from fastapi.openapi.utils import get_openapi

_openapi_schema_cache = None
def custom_openapi():
    global _openapi_schema_cache
    if _openapi_schema_cache:
        return _openapi_schema_cache
    schema = get_openapi(
        title="Mad Dog Mock",
        version="1.0.0",
        description="API para cadastro de cenários e mocks dinâmicos com variantes e validação JWT.",
        routes=app.routes,
    )
    schema["externalDocs"] = {
        "description": "Guia completo (HTML)",
        "url": "/docs/guide.html"
    }
    _openapi_schema_cache = schema
    return schema

app.openapi = custom_openapi
