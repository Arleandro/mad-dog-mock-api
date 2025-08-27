from __future__ import annotations
from typing import List
from fastapi import Depends, APIRouter, HTTPException
from ..storage.memory import InMemoryStore
from ..di import get_store
from ..models import Mock, MockCreate, MockUpdate

router = APIRouter(tags=["mocks"])

@router.get("/api/mocks", response_model=List[Mock])
async def list_mocks(store: InMemoryStore = Depends(get_store)) -> List[Mock]:
    return await store.list_mocks()

@router.get("/api/mocks/{mock_id}", response_model=Mock)
async def get_mock(mock_id: str, store: InMemoryStore = Depends(get_store)) -> Mock:
    try: return await store.get_mock(mock_id)
    except KeyError: raise HTTPException(status_code=404, detail="Mock not found")

@router.post("/api/mocks", response_model=Mock, status_code=201)
async def create_mock(m: MockCreate, store: InMemoryStore = Depends(get_store)) -> Mock:
    try: return await store.create_mock(m)
    except KeyError: raise HTTPException(status_code=404, detail="Scenario not found")
    except FileExistsError: raise HTTPException(status_code=409, detail="Mock already exists for this scenario/method/uri. Use PUT to update.")

@router.put("/api/mocks/{mock_id}", response_model=Mock)
async def update_mock(mock_id: str, patch: MockUpdate, store: InMemoryStore = Depends(get_store)) -> Mock:
    try: return await store.update_mock(mock_id, patch)
    except KeyError: raise HTTPException(status_code=404, detail="Mock not found")

@router.delete("/api/mocks/{mock_id}", status_code=204)
async def delete_mock(mock_id: str, store: InMemoryStore = Depends(get_store)):
    await store.delete_mock(mock_id); return {}
