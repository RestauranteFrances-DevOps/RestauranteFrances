import math
import json
import sqlite3
import time
import hashlib
from typing import List, Dict, Optional

# overpy (Overpass) — optional
try:
    import overpy
    _HAS_OVERPY = True
except Exception:
    _HAS_OVERPY = False

# rapidfuzz optional for fuzzy matching
try:
    from rapidfuzz import fuzz
    _HAS_FUZZY = True
except Exception:
    fuzz = None
    _HAS_FUZZY = False

CACHE_DB = "overpass_cache.db"

def _init_cache():
    conn = sqlite3.connect(CACHE_DB)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, ts INTEGER, payload TEXT)"
    )
    conn.commit()
    conn.close()

def _cache_get(key: str, max_age_s: int) -> Optional[List[Dict]]:
    try:
        conn = sqlite3.connect(CACHE_DB)
        cur = conn.cursor()
        cur.execute("SELECT ts, payload FROM cache WHERE k = ?", (key,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        ts, payload = row
        if time.time() - ts > max_age_s:
            return None
        return json.loads(payload)
    except Exception:
        return None

def _cache_set(key: str, value: List[Dict]):
    try:
        conn = sqlite3.connect(CACHE_DB)
        cur = conn.cursor()
        cur.execute("REPLACE INTO cache (k, ts, payload) VALUES (?, ?, ?)",
                    (key, int(time.time()), json.dumps(value, ensure_ascii=False)))
        conn.commit()
        conn.close()
    except Exception:
        pass

def _make_cache_key(lat: float, lon: float, raio: int, especialidade: Optional[str], max_results: int) -> str:
    s = f"{lat:.6f}:{lon:.6f}:{raio}:{(especialidade or '').lower()}:{max_results}"
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _to_float(v):
    try:
        return float(v)
    except Exception:
        return None

def _match_especialidade(nome, espec_field, query, fuzzy_threshold=70):
    if not query:
        return True
    q = str(query).strip().lower()
    if nome and q in str(nome).lower():
        return True
    if espec_field and q in str(espec_field).lower():
        return True
    if _HAS_FUZZY:
        try:
            if nome and fuzz.token_set_ratio(q, str(nome).lower()) >= fuzzy_threshold:
                return True
            if espec_field and fuzz.token_set_ratio(q, str(espec_field).lower()) >= fuzzy_threshold:
                return True
        except Exception:
            pass
    return False

# sensible public endpoints to try when overpy default fails
_DEFAULT_OVERPASS_ENDPOINTS = [
    None,  # None lets overpy use its default
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

def _query_overpass(lat, lon, raio, especialidade, max_results, overpass_url=None, cache_ttl_hours=12):
    """
    Attempts to query Overpass, with multiple endpoints and caching.
    Returns a list of simple dicts (JSON-serializable).
    """
    _init_cache()
    cache_key = _make_cache_key(lat, lon, raio, especialidade, max_results)
    cached = _cache_get(cache_key, int(cache_ttl_hours * 3600))
    if cached is not None:
        return cached

    endpoints = [overpass_url] if overpass_url else []
    endpoints.extend([e for e in _DEFAULT_OVERPASS_ENDPOINTS if e not in endpoints])

    q = (
        "[out:json];\n"
        "(\n"
        f"  node(around:{int(raio)},{lat},{lon})[amenity=veterinary];\n"
        f"  way(around:{int(raio)},{lat},{lon})[amenity=veterinary];\n"
        f"  relation(around:{int(raio)},{lat},{lon})[amenity=veterinary];\n"
        ");\n"
        f"out center {max_results};\n"
    )

    last_exc = None
    results = []
    for endpoint in endpoints:
        # try up to 3 attempts per endpoint with backoff
        for attempt in range(3):
            try:
                api = overpy.Overpass(url=endpoint) if endpoint else overpy.Overpass()
                res = api.query(q)  # compatible with common overpy versions
                # parse nodes
                for n in getattr(res, "nodes", []):
                    nlat = _to_float(getattr(n, "lat", None)); nlon = _to_float(getattr(n, "lon", None))
                    if nlat is None or nlon is None: continue
                    tags = getattr(n, "tags", {}) or {}
                    nome = tags.get("name")
                    endereco = tags.get("addr:street") or tags.get("addr:full") or ""
                    telefone = tags.get("phone") or tags.get("contact:phone")
                    spec = tags.get("vet:speciality") or tags.get("speciality") or tags.get("service")
                    if not _match_especialidade(nome, spec, especialidade):
                        continue
                    dist = _haversine_m(lat, lon, nlat, nlon)
                    results.append({
                        "nome": nome or "Clínica Veterinária",
                        "endereco": endereco or "",
                        "lat": nlat,
                        "lon": nlon,
                        "telefone": telefone,
                        "especialidade": spec,
                        "distancia_m": dist,
                        "source": "overpass"
                    })
                # parse ways
                for w in getattr(res, "ways", []):
                    if not (hasattr(w, "center_lat") and hasattr(w, "center_lon")): continue
                    wlat = _to_float(getattr(w, "center_lat", None)); wlon = _to_float(getattr(w, "center_lon", None))
                    if wlat is None or wlon is None: continue
                    tags = getattr(w, "tags", {}) or {}
                    nome = tags.get("name")
                    endereco = tags.get("addr:street") or tags.get("addr:full") or ""
                    telefone = tags.get("phone") or tags.get("contact:phone")
                    spec = tags.get("vet:speciality") or tags.get("speciality")
                    if not _match_especialidade(nome, spec, especialidade):
                        continue
                    dist = _haversine_m(lat, lon, wlat, wlon)
                    results.append({
                        "nome": nome or "Clínica Veterinária",
                        "endereco": endereco or "",
                        "lat": wlat,
                        "lon": wlon,
                        "telefone": telefone,
                        "especialidade": spec,
                        "distancia_m": dist,
                        "source": "overpass"
                    })
                # parse relations
                for r in getattr(res, "relations", []):
                    if not (hasattr(r, "center_lat") and hasattr(r, "center_lon")): continue
                    rlat = _to_float(getattr(r, "center_lat", None)); rlon = _to_float(getattr(r, "center_lon", None))
                    if rlat is None or rlon is None: continue
                    tags = getattr(r, "tags", {}) or {}
                    nome = tags.get("name")
                    endereco = tags.get("addr:street") or tags.get("addr:full") or ""
                    telefone = tags.get("phone") or tags.get("contact:phone")
                    spec = tags.get("vet:speciality") or tags.get("speciality")
                    if not _match_especialidade(nome, spec, especialidade):
                        continue
                    dist = _haversine_m(lat, lon, rlat, rlon)
                    results.append({
                        "nome": nome or "Clínica Veterinária",
                        "endereco": endereco or "",
                        "lat": rlat,
                        "lon": rlon,
                        "telefone": telefone,
                        "especialidade": spec,
                        "distancia_m": dist,
                        "source": "overpass"
                    })
                # success: cache and return
                if results:
                    payload = []
                    for it in results:
                        payload.append({
                            "nome": it.get("nome"),
                            "endereco": it.get("endereco"),
                            "lat": float(it.get("lat")),
                            "lon": float(it.get("lon")),
                            "telefone": it.get("telefone"),
                            "especialidade": it.get("especialidade"),
                            "distancia_m": float(it.get("distancia_m")),
                            "source": it.get("source")
                        })
                    _cache_set(cache_key, payload)
                    return payload
                else:
                    return []
            except Exception as e:
                last_exc = e
                time.sleep( (2 ** attempt) )
                continue
    if last_exc:
        print("Aviso Overpass:", last_exc)
    return []

def buscar_clinicas_veterinarias(lat, lon, raio=5000, especialidade=None, use_overpass=True, re_rank=True, max_results=50, overpass_url=None, cache_ttl_hours=12, fuzzy_threshold=70):
    """
    Interface principal.
    """
    results = []
    demo = [
        {"nome": "Clínica Vet Demo 1", "lat": lat, "lon": lon},
        {"nome": "Clínica Vet Demo 2", "lat": lat + 0.0005, "lon": lon - 0.0007},
        {"nome": "Clínica Vet Demo 3", "lat": lat + 0.001, "lon": lon + 0.0015},
    ]
    for d in demo:
        dlat = _to_float(d["lat"]); dlon = _to_float(d["lon"])
        if dlat is None or dlon is None: continue
        results.append({
            "nome": d["nome"],
            "endereco": "",
            "lat": dlat,
            "lon": dlon,
            "telefone": None,
            "especialidade": None,
            "distancia_m": _haversine_m(lat, lon, dlat, dlon),
            "source": "offline"
        })

    if use_overpass and _HAS_OVERPY:
        overpass_hits = _query_overpass(lat, lon, raio, especialidade, max_results, overpass_url, cache_ttl_hours)
        for it in overpass_hits:
            results.append(it)

    seen = set()
    unique = []
    for it in sorted(results, key=lambda x: x.get("distancia_m", float("inf"))):
        key = (round(it.get("lat", 0), 6), round(it.get("lon", 0), 6))
        if key in seen: continue
        seen.add(key)
        unique.append(it)

    if re_rank:
        unique.sort(key=lambda x: x.get("distancia_m", float("inf")))

    return unique[:max_results]
