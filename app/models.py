from __future__ import annotations
import re, uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict

HttpMethod = Literal["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"]

class RequestParam(BaseModel):
    name: str
    in_: Literal["query","path","header"] = Field(alias="in", default="query")
    description: Optional[str] = None
    schema_type: Literal["string","number","integer","boolean","array","object"] = "string"
    required: bool = False
    example: Optional[Any] = None

class ConditionPredicate(BaseModel):
    source: Literal["header","query","path","body","jwt_header","jwt_payload"]
    key: Optional[str] = None
    jsonpath: Optional[str] = None
    op: Literal["equals","regex","contains","in"] = "equals"
    value: Optional[Union[str,int,float,bool]] = None
    values: Optional[List[Union[str,int,float,bool]]] = None

class MockResponse(BaseModel):
    status_code: int = Field(200, ge=100, le=599)
    headers: Optional[Dict[str,str]] = None
    media_type: str = "application/json"
    body: Optional[Any] = None
    description: Optional[str] = None

class ResponseVariant(BaseModel):
    description: Optional[str] = None
    when: List[ConditionPredicate] = Field(default_factory=list)
    response: MockResponse

class MockRequestMatch(BaseModel):
    method: HttpMethod
    uri: str
    content_type: Optional[str] = "application/json"
    example_body: Optional[Any] = None
    query: Optional[Dict[str,str]] = None
    headers: Optional[Dict[str,str]] = None
    body: Optional[Any] = None
    params: Optional[List[RequestParam]] = Field(default_factory=list)

class Mock(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_basepath: str
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    request: MockRequestMatch
    response: MockResponse
    variants: Optional[List[ResponseVariant]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MockCreate(BaseModel):
    scenario_basepath: str
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    request: MockRequestMatch
    response: MockResponse
    variants: Optional[List[ResponseVariant]] = Field(default_factory=list)

class MockUpdate(BaseModel):
    scenario_basepath: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    request: Optional[MockRequestMatch] = None
    response: Optional[MockResponse] = None
    variants: Optional[List[ResponseVariant]] = None

class Scenario(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    basepath: str
    enabled: bool = True
    jwt_issuer_url: Optional[str] = None
    jwt_location: Literal["none","header","cookie"] = "none"
    jwt_header_name: Optional[str] = "Authorization"
    jwt_is_bearer: Optional[bool] = True
    jwt_cookie_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ScenarioCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    basepath: Optional[str] = None
    enabled: Optional[bool] = True
    jwt_issuer_url: Optional[str] = None
    jwt_location: Optional[Literal["none","header","cookie"]] = "none"
    jwt_header_name: Optional[str] = "Authorization"
    jwt_is_bearer: Optional[bool] = True
    jwt_cookie_name: Optional[str] = None

class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    basepath: Optional[str] = None
    enabled: Optional[bool] = None
    jwt_issuer_url: Optional[str] = None
    jwt_location: Optional[Literal["none","header","cookie"]] = None
    jwt_header_name: Optional[str] = None
    jwt_is_bearer: Optional[bool] = None
    jwt_cookie_name: Optional[str] = None

def ensure_leading_slash(p: str) -> str:
    return p if p.startswith("/") else "/" + p

def pattern_to_regex_with_params(pattern: str):
    if pattern.startswith("^") and pattern.endswith("$"):
        import re
        return re.compile(pattern), []
    import re
    regex, param_names, i = "", [], 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "{":
            j = pattern.find("}", i+1)
            if j == -1: regex += re.escape(ch); i += 1
            else:
                name = pattern[i+1:j] or f"p{len(param_names)}"
                param_names.append(name)
                regex += f"(?P<{re.escape(name)}>[^/]+)"
                i = j + 1
        elif ch == "*":
            regex += ".*"; i += 1
        else:
            regex += re.escape(ch); i += 1
    return re.compile("^" + regex + "$"), param_names

def specificity_score(pattern: str) -> int:
    score = 0; i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "{":
            j = pattern.find("}", i+1)
            if j == -1: score += 1; i += 1
            else: i = j + 1
        elif ch == "*":
            i += 1
        else:
            score += 1; i += 1
    return score
