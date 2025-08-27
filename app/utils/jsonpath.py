from typing import Any
def jsonpath_get(expr: str, obj: Any) -> Any:
    if not isinstance(expr, str) or not expr.startswith('$.'): return None
    parts = expr[2:].split('.'); cur = obj
    for part in parts:
        if '[' in part:
            name, rest = part.split('[', 1)
            if name:
                if not isinstance(cur, dict): return None
                cur = cur.get(name)
            while rest:
                if not rest.startswith(']'):
                    idx_str, rest = rest.split(']', 1)
                    try: idx = int(idx_str)
                    except: return None
                    if not isinstance(cur, list) or idx >= len(cur): return None
                    cur = cur[idx]
                    if rest.startswith('['): rest = rest[1:]
                    else: break
                else:
                    rest = rest[1:]
        else:
            if not isinstance(cur, dict): return None
            cur = cur.get(part)
        if cur is None: return None
    return cur
