# ai_actions.py - connects geocoding (Nominatim), OSM Overpass and ranking with feedback
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from db import get_geocode_from_cache, set_geocode_cache, get_overpass_from_cache, set_overpass_cache, log_search, get_feedback_score
import overpy, time, hashlib
from distancia import ordenar_por_distancia
import math

USER_AGENT = "ComunicaVET/1.0 (contato@example.com)"
geolocator = Nominatim(user_agent=USER_AGENT)
api = overpy.Overpass()

def obter_coordenadas(endereco: str):
    cached = get_geocode_from_cache(endereco)
    if cached: return cached['lat'], cached['lon']
    time.sleep(1.0)
    try:
        loc = geolocator.geocode(endereco, timeout=10)
    except GeocoderTimedOut:
        time.sleep(1.5)
        loc = geolocator.geocode(endereco, timeout=15)
    if not loc:
        raise ValueError("Endereço não encontrado.")
    set_geocode_cache(endereco, loc.latitude, loc.longitude)
    return loc.latitude, loc.longitude

def _make_cache_key(lat, lon, raio):
    s = f"{lat:.6f}:{lon:.6f}:{raio}"
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


import os
import json
import math
import sqlite3

def _haversine_m(lat1, lon1, lat2, lon2):
    # retorna distância em metros
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _get_latlon_from_row(row, cols):
    # tenta achar colunas que representem lat/lon e nome/endereco em uma linha de DB
    lat_keys = [k for k in cols if k.lower() in ("lat", "latitude", "latitude_deg", "y")]
    lon_keys = [k for k in cols if k.lower() in ("lon", "longitude", "lng", "longitude_deg", "x")]
    name_keys = [k for k in cols if "nome" in k.lower() or "name" in k.lower() or "title" in k.lower()]
    addr_keys = [k for k in cols if "endereco" in k.lower() or "address" in k.lower() or "addr" in k.lower()]

    def get_val(keys):
        for k in keys:
            if k in cols:
                return row[cols.index(k)]
        return None

    lat = get_val(lat_keys)
    lon = get_val(lon_keys)
    name = get_val(name_keys) or get_val(addr_keys) or None
    addr = get_val(addr_keys) or None

    try:
        if lat is not None:
            lat = float(lat)
        if lon is not None:
            lon = float(lon)
    except Exception:
        lat = None
        lon = None

    return name, addr, lat, lon


import os
import json
import math
import sqlite3
import time

# try to import overpy if available (Overpass)
try:
    import overpy
    _HAS_OVERPY = True
except Exception:
    _HAS_OVERPY = False

# try to import get_feedback_score if project provides it
try:
    from db import get_feedback_score
    _HAS_FEEDBACK = True
except Exception:
    _HAS_FEEDBACK = False

def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _get_val_ci(obj, *keys):
    # retorna o primeiro valor encontrado (case-insensitive) entre keys
    for k in keys:
        if k in obj:
            return obj[k]
    for key in obj:
        for k in keys:
            if key.lower() == k.lower():
                return obj[key]
    return None

def _get_latlon_from_row_with_fields(row, cols):
    # procura lat/lon, nome, endereco, telefone, especialidade em row/cols
    cols_l = [c for c in cols]
    def get_val_matching(key_candidates):
        for c in cols_l:
            for cand in key_candidates:
                if cand.lower() in c.lower():
                    return row[cols_l.index(c)]
        return None

    lat = get_val_matching(("lat","latitude","latitude_deg","y"))
    lon = get_val_matching(("lon","longitude","lng","longitude_deg","x"))
    name = get_val_matching(("nome","name","title","nome_fantasia","fantasia"))
    addr = get_val_matching(("endereco","address","addr","logradouro"))
    phone = get_val_matching(("telefone","phone","fone","tel"))
    spec = get_val_matching(("especialidade","especial","especialidades","specialty","spec"))

    try:
        if lat is not None:
            lat = float(lat)
        if lon is not None:
            lon = float(lon)
    except Exception:
        lat = None
        lon = None

    return name, addr, lat, lon, phone, spec

def _overpass_query(lat, lon, raio, filtro_especialidade=None, max_results=50):
    """
    Consulta Overpass (se available). Retorna lista de dicts com nome, endereco, lat, lon, telefone, tags.
    """
    if not _HAS_OVERPY:
        return []

    api = overpy.Overpass()
    # procurar nodes e ways com amenity=veterinary ou veterinary; filtra tags name, phone, speciality-like
    # usar around para performance
    try:
        # build a simple query — OSM tag 'amenity=veterinary' is common
        q = f"""
        (
          node(around:{int(raio)},{lat},{lon})[amenity=veterinary];
          way(around:{int(raio)},{lat},{lon})[amenity=veterinary];
          relation(around:{int(raio)},{lat},{lon})[amenity=veterinary];
        );
        out center {max_results};
        """
        res = api.query(q, timeout=60)
        items = []
        def _add_node(n, lat_, lon_):
            tags = n.tags if hasattr(n, "tags") else {}
            name = tags.get("name")
            phone = tags.get("phone") or tags.get("contact:phone")
            addr = ", ".join(filter(None, [
                tags.get("addr:street"),
                tags.get("addr:housenumber"),
                tags.get("addr:city")
            ])) if tags else ""
            spec = tags.get("speciality") or tags.get("vet:speciality") or tags.get("vet:speciality:en")
            items.append({
                "nome": name or "Clinica (OSM)",
                "endereco": addr,
                "lat": float(lat_),
                "lon": float(lon_),
                "telefone": phone,
                "especialidade": spec,
                "tags": tags
            })
        # nodes
        for n in res.nodes:
            _add_node(n, n.lat, n.lon)
        # ways/relations: use center
        for w in getattr(res, "ways", []):
            if hasattr(w, "center_lat") and hasattr(w, "center_lon"):
                _add_node(w, w.center_lat, w.center_lon)
        for r in getattr(res, "relations", []):
            if hasattr(r, "center_lat") and hasattr(r, "center_lon"):
                _add_node(r, r.center_lat, r.center_lon)
        # optional: filter by especialidade keyword if provided (search in tags)
        if filtro_especialidade:
            kw = filtro_especialidade.lower()
            items = [it for it in items if (it.get("especialidade") and kw in str(it.get("especialidade")).lower()) or (it.get("tags") and any(kw in str(v).lower() for v in it["tags"].values())) or (it.get("nome") and kw in it["nome"].lower())]
        return items[:max_results]
    except Exception:
        return []


import os
import json
import math
import sqlite3
import time

try:
    import overpy
    _HAS_OVERPY = True
except Exception:
    _HAS_OVERPY = False

try:
    from db import get_feedback_score
    _HAS_FEEDBACK = True
except Exception:
    _HAS_FEEDBACK = False

def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _get_val_ci(obj, *keys):
    for k in keys:
        if k in obj:
            return obj[k]
    for key in obj:
        for k in keys:
            if key.lower() == k.lower():
                return obj[key]
    return None

def _get_latlon_from_row_with_fields(row, cols):
    cols_l = [c for c in cols]
    def get_val_matching(key_candidates):
        for c in cols_l:
            for cand in key_candidates:
                if cand.lower() in c.lower():
                    return row[cols_l.index(c)]
        return None

    lat = get_val_matching(("lat","latitude","latitude_deg","y"))
    lon = get_val_matching(("lon","longitude","lng","longitude_deg","x"))
    name = get_val_matching(("nome","name","title","nome_fantasia","fantasia"))
    addr = get_val_matching(("endereco","address","addr","logradouro"))
    phone = get_val_matching(("telefone","phone","fone","tel"))
    spec = get_val_matching(("especialidade","especial","especialidades","specialty","spec"))

    try:
        if lat is not None:
            lat = float(lat)
        if lon is not None:
            lon = float(lon)
    except Exception:
        lat = None
        lon = None

    return name, addr, lat, lon, phone, spec

def _overpass_query(lat, lon, raio, filtro_especialidade=None, max_results=50):
    if not _HAS_OVERPY:
        return []
    api = overpy.Overpass()
    try:
        q = f"""
        (
          node(around:{int(raio)},{lat},{lon})[amenity=veterinary];
          way(around:{int(raio)},{lat},{lon})[amenity=veterinary];
          relation(around:{int(raio)},{lat},{lon})[amenity=veterinary];
        );
        out center {max_results};
        """
        res = api.query(q, timeout=60)
        items = []
        def _add_node(n, lat_, lon_):
            tags = n.tags if hasattr(n, "tags") else {}
            name = tags.get("name")
            phone = tags.get("phone") or tags.get("contact:phone")
            addr = ", ".join(filter(None, [
                tags.get("addr:street"),
                tags.get("addr:housenumber"),
                tags.get("addr:city")
            ])) if tags else ""
            spec = tags.get("speciality") or tags.get("vet:speciality")
            items.append({
                "nome": name or "Clinica (OSM)",
                "endereco": addr,
                "lat": float(lat_),
                "lon": float(lon_),
                "telefone": phone,
                "especialidade": spec,
                "tags": tags
            })
        for n in res.nodes:
            _add_node(n, n.lat, n.lon)
        for w in getattr(res, "ways", []):
            if hasattr(w, "center_lat") and hasattr(w, "center_lon"):
                _add_node(w, w.center_lat, w.center_lon)
        for r in getattr(res, "relations", []):
            if hasattr(r, "center_lat") and hasattr(r, "center_lon"):
                _add_node(r, r.center_lat, r.center_lon)
        if filtro_especialidade:
            kw = filtro_especialidade.lower()
            items = [it for it in items if (it.get("especialidade") and kw in str(it.get("especialidade")).lower()) or (it.get("tags") and any(kw in str(v).lower() for v in it["tags"].values())) or (it.get("nome") and kw in it["nome"].lower())]
        return items[:max_results]
    except Exception:
        return []


import math

try:
    import overpy
    _HAS_OVERPY = True
except Exception:
    _HAS_OVERPY = False

def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _to_float(val):
    """Converte Decimal/str/float pra float ou retorna None."""
    try:
        return float(val)
    except Exception:
        return None

def _match_especialidade(nome, especialidade_field, query):
    """Retorna True se query (lower) é substring de nome ou do campo especialidade."""
    if not query:
        return True
    q = str(query).strip().lower()
    if nome and q in str(nome).lower():
        return True
    if especialidade_field and q in str(especialidade_field).lower():
        return True
    return False



def buscar_clinicas_veterinarias(*args, **kwargs):
    """Wrapper seguro — delega para new_buscar_clinicas.buscar_clinicas_veterinarias"""
    try:
        from new_buscar_clinicas import buscar_clinicas_veterinarias as _new_buscar
    except Exception as e:
        raise RuntimeError("Erro ao importar new_buscar_clinicas: " + str(e))
    return _new_buscar(*args, **kwargs)


