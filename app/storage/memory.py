from __future__ import annotations
import asyncio, re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from ..models import (
    Mock, MockCreate, MockUpdate, Scenario, ScenarioCreate, ScenarioUpdate,
    pattern_to_regex_with_params, ensure_leading_slash, specificity_score
)

class InMemoryStore:
    def __init__(self):
        self._mocks: Dict[str, Dict[str, Any]] = {}
        self._scenarios: Dict[str, Dict[str, Any]] = {}
        self._compiled_mock_uri: Dict[str, tuple] = {}
        self._lock = asyncio.Lock()

    async def list_scenarios(self) -> List[Scenario]:
        async with self._lock:
            return [Scenario(**d) for d in self._scenarios.values()]

    async def get_scenario(self, basepath: str) -> Scenario:
        async with self._lock:
            basepath = ensure_leading_slash(basepath)
            s = self._scenarios.get(basepath)
            if not s: raise KeyError(basepath)
            return Scenario(**s)

    async def create_scenario(self, sc: ScenarioCreate) -> Scenario:
        async with self._lock:
            if not sc.basepath: raise ValueError("basepath is required")
            basepath = ensure_leading_slash(sc.basepath.strip())
            if basepath in self._scenarios: raise ValueError("Basepath already in use by another scenario")
            scenario = Scenario(
                id=basepath, name=sc.name, description=sc.description, basepath=basepath,
                enabled=True if sc.enabled is None else sc.enabled,
                jwt_issuer_url=sc.jwt_issuer_url, jwt_location=sc.jwt_location or "none",
                jwt_header_name=sc.jwt_header_name or "Authorization",
                jwt_is_bearer=True if sc.jwt_is_bearer is None else sc.jwt_is_bearer,
                jwt_cookie_name=sc.jwt_cookie_name,
            )
            self._scenarios[basepath] = scenario.model_dump()
            return scenario

    async def update_scenario(self, basepath: str, patch: ScenarioUpdate) -> Scenario:
        async with self._lock:
            basepath = ensure_leading_slash(basepath)
            if basepath not in self._scenarios: raise KeyError(basepath)
            doc = self._scenarios[basepath]
            new_basepath = doc["basepath"]
            if patch.basepath and patch.basepath.strip():
                cand = ensure_leading_slash(patch.basepath.strip())
                if cand != basepath and cand in self._scenarios:
                    raise ValueError("Basepath already in use by another scenario")
                new_basepath = cand
            if patch.name is not None: doc["name"] = patch.name
            if patch.description is not None: doc["description"] = patch.description
            if patch.enabled is not None: doc["enabled"] = patch.enabled
            if patch.jwt_issuer_url is not None: doc["jwt_issuer_url"] = patch.jwt_issuer_url
            if patch.jwt_location is not None: doc["jwt_location"] = patch.jwt_location
            if patch.jwt_header_name is not None: doc["jwt_header_name"] = patch.jwt_header_name
            if patch.jwt_is_bearer is not None: doc["jwt_is_bearer"] = patch.jwt_is_bearer
            if patch.jwt_cookie_name is not None: doc["jwt_cookie_name"] = patch.jwt_cookie_name
            doc["updated_at"] = datetime.now(timezone.utc)
            if new_basepath != basepath:
                doc["basepath"] = new_basepath; doc["id"] = new_basepath
                self._scenarios.pop(basepath); self._scenarios[new_basepath] = doc
                for mid, m in list(self._mocks.items()):
                    if m["scenario_basepath"] == basepath:
                        m["scenario_basepath"] = new_basepath
            else:
                self._scenarios[basepath] = doc
            return Scenario(**doc)

    async def delete_scenario(self, basepath: str) -> None:
        async with self._lock:
            basepath = ensure_leading_slash(basepath)
            if basepath in self._scenarios:
                for mid, m in list(self._mocks.items()):
                    if m["scenario_basepath"] == basepath:
                        self._mocks.pop(mid, None); self._compiled_mock_uri.pop(mid, None)
                self._scenarios.pop(basepath, None)

    async def list_mocks(self) -> List[Mock]:
        async with self._lock:
            return [Mock(**doc) for doc in self._mocks.values()]

    async def get_mock(self, mock_id: str) -> Mock:
        async with self._lock:
            doc = self._mocks.get(mock_id)
            if not doc: raise KeyError(mock_id)
            return Mock(**doc)

    async def _ensure_scenario_exists(self, basepath: str) -> Scenario:
        if ensure_leading_slash(basepath) not in self._scenarios: raise KeyError("Scenario not found")
        return Scenario(**self._scenarios[ensure_leading_slash(basepath)])

    async def create_mock(self, m: MockCreate) -> Mock:
        async with self._lock:
            if not m.scenario_basepath: raise KeyError("Scenario not found")
            await self._ensure_scenario_exists(m.scenario_basepath)
            for doc in self._mocks.values():
                if doc["scenario_basepath"] == ensure_leading_slash(m.scenario_basepath) and \
                   doc["request"]["method"].upper() == m.request.method.upper() and \
                   doc["request"]["uri"] == m.request.uri:
                    raise FileExistsError("Mock already exists for this scenario/method/uri. Use PUT to update.")
            mock = Mock(**m.model_dump())
            mock.scenario_basepath = ensure_leading_slash(mock.scenario_basepath)
            self._mocks[mock.id] = mock.model_dump()
            self._compiled_mock_uri[mock.id] = pattern_to_regex_with_params(mock.request.uri)
            return mock

    async def update_mock(self, mock_id: str, patch: MockUpdate) -> Mock:
        async with self._lock:
            if mock_id not in self._mocks: raise KeyError(mock_id)
            doc = self._mocks[mock_id]
            if patch.scenario_basepath is not None:
                await self._ensure_scenario_exists(patch.scenario_basepath)
                doc["scenario_basepath"] = ensure_leading_slash(patch.scenario_basepath)
            for k, v in patch.model_dump(exclude_unset=True).items():
                if k in ("scenario_basepath",): continue
                if k == "request" and v is not None: doc["request"] = v
                elif k == "response" and v is not None: doc["response"] = v
                elif k == "variants" and v is not None: doc["variants"] = v
                else: doc[k] = v
            doc["updated_at"] = datetime.now(timezone.utc)
            self._mocks[mock_id] = doc
            self._compiled_mock_uri[mock_id] = pattern_to_regex_with_params(doc["request"]["uri"])
            return Mock(**doc)

    async def delete_mock(self, mock_id: str) -> None:
        async with self._lock:
            self._mocks.pop(mock_id, None); self._compiled_mock_uri.pop(mock_id, None)

    async def find_match(self, path: str, method: str, query: Dict[str,str], headers: Dict[str,str], body: Any):
        async with self._lock:
            cands = []
            for basepath, sdoc in self._scenarios.items():
                if not sdoc.get("enabled", True): continue
                bp = sdoc["basepath"]
                if path == bp or path.startswith(bp.rstrip("/") + "/"):
                    cands.append(Scenario(**sdoc))
            if not cands: return None
            scenario = sorted(cands, key=lambda s: len(s.basepath), reverse=True)[0]
            sub = path[len(scenario.basepath):] or "/"
            if not sub.startswith("/"): sub = "/" + sub
            picks = []
            for doc in self._mocks.values():
                m = Mock(**doc)
                if not m.enabled or m.scenario_basepath != scenario.basepath: continue
                if m.request.method.upper() != method.upper(): continue
                regex, _ = self._compiled_mock_uri.get(m.id) or pattern_to_regex_with_params(m.request.uri)
                mt = regex.match(sub)
                if not mt: continue
                path_params = {k: mt.group(k) for k in mt.groupdict().keys()}
                if m.request.query and any(query.get(k) != v for k,v in m.request.query.items()): continue
                if m.request.headers and any(headers.get(k.lower()) != v for k,v in m.request.headers.items()): continue
                if m.request.body is not None:
                    import json as _json
                    if isinstance(m.request.body, (dict,list)):
                        if not isinstance(body, (dict,list)) or body != m.request.body: continue
                    else:
                        if (body if isinstance(body,str) else _json.dumps(body, separators=(',',':'), ensure_ascii=False)) != str(m.request.body): continue
                score = m.priority * 100000 + specificity_score(m.request.uri)
                picks.append((score, m, path_params, scenario))
            if not picks: return None
            picks.sort(key=lambda x: x[0], reverse=True)
            return picks[0][1], picks[0][2], picks[0][3]
