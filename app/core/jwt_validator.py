from __future__ import annotations
import time
from typing import Any, Dict, Optional, Tuple
from jose import jwt
import httpx
from .config import JWKS_TTL, HTTP_TIMEOUT

class JWKSCache:
    def __init__(self): self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    def get(self, issuer: str) -> Optional[Dict[str, Any]]:
        it = self._cache.get(issuer)
        if not it: return None
        exp, jwks = it
        if time.time() > exp: self._cache.pop(issuer, None); return None
        return jwks
    def set(self, issuer: str, jwks: Dict[str, Any]):
        self._cache[issuer] = (time.time() + JWKS_TTL, jwks)

jwks_cache = JWKSCache()

async def fetch_jwks_for_issuer(issuer_url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, verify=True) as client:
        if not issuer_url.endswith('/'):
            issuer_url += '/'
        wk = issuer_url + '.well-known/openid-configuration'
        r = await client.get(wk); r.raise_for_status()
        conf = r.json(); jwks_uri = conf.get('jwks_uri')
        if not jwks_uri: raise RuntimeError('jwks_uri not found in openid-configuration')
        r2 = await client.get(jwks_uri); r2.raise_for_status()
        return r2.json()

async def validate_jwt(token: str, issuer_url: str) -> Dict[str, Any]:
    if not issuer_url.lower().startswith('https://'):
        raise RuntimeError('Issuer URL must be HTTPS')
    jwks = jwks_cache.get(issuer_url)
    if jwks is None:
        jwks = await fetch_jwks_for_issuer(issuer_url)
        jwks_cache.set(issuer_url, jwks)
    last_err = None
    for key in jwks.get('keys', []):
        try:
            payload = jwt.decode(token, key, algorithms=[key.get('alg','RS256')], options={'verify_aud': False}, issuer=issuer_url.rstrip('/'))
            header = jwt.get_unverified_header(token)
            print('*********************JSON TOKEN JWT Request:')
            print({'header': header, 'payload': payload})
            return {'header': header, 'payload': payload}
        except Exception as e:
            last_err = e; continue
    if last_err: raise last_err
    raise RuntimeError('No JWKS keys available for validation')
