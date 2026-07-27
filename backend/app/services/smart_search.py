"""Ricerca "intelligente": non solo titoli, ma anche persone, studi e temi.

Cercare `marvel` deve dare i film Marvel, `nolan` i film di Nolan, `zombie` i film di
zombie — non solo i titoli che contengono quella parola. Per farlo, oltre alla ricerca
per titolo interroghiamo `/search/person`, `/search/company` e `/search/keyword`: per le
entità che corrispondono *davvero* alla query tiriamo giù i titoli collegati e li
accodiamo ai risultati per titolo.

Tutte le chiamate passano da `tmdb_get`, quindi sono in cache: la stessa query digitata
da un altro utente (o la pagina 2 chiesta subito dopo) non ricontatta TMDB.
"""

import asyncio
import math
import unicodedata

from ..tmdb import tmdb_get

_PAGE_SIZE = 20      # dimensione pagina di TMDB
_MAX_PAGES = 500     # oltre la 500 TMDB dà errore
_MIN_QUERY_LEN = 3   # sotto i 3 caratteri l'espansione è solo rumore (e ~8 chiamate)
_ENTITY_TTL = 21600  # 6h: persone, studi e keyword non cambiano quasi mai

_MAX_COMPANIES = 3   # "marvel" → Marvel Studios + Marvel Entertainment + ...
_MAX_KEYWORDS = 2

# Ruoli di troupe che rendono un titolo "di" quella persona. Niente produttori o
# reparti tecnici: cercando un regista si vogliono i suoi film, non tutti quelli
# in cui compare nei titoli di coda.
_CREW_JOBS = {"Director", "Series Director", "Writer", "Screenplay", "Story", "Creator"}

# Ordine dei blocchi a parità di punteggio: un nome-marchio è quasi sempre lo studio.
_PRIORITY = {"company": 0, "keyword": 1, "person": 2}


def _norm(s: str) -> str:
    """Minuscolo e senza accenti, per confrontare "Bong Joon-ho" con "bong joon-ho"."""
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def _score(name: str, q: str) -> int:
    """Quanto la query "punta" a questa entità: 0 = per niente, 3 = in pieno.

    TMDB restituisce match molto laschi (cercando "mar" escono decine di persone): senza
    questa soglia finiremmo per mescolare ai risultati la filmografia di chiunque.
    """
    n, qq = _norm(name), _norm(q)
    if not n or not qq:
        return 0
    if n == qq:
        return 3                       # "christopher nolan" → Christopher Nolan
    if len(qq) >= 4 and n.startswith(qq):
        return 2                       # "robert downey" → Robert Downey Jr.
    if qq in n.split():
        return 1                       # "nolan" → Christopher Nolan
    return 0


def _pick(results: list | None, q: str, limit: int) -> list[tuple[int, dict]]:
    """Le entità che corrispondono alla query, dalla più pertinente."""
    scored = [(s, r) for r in (results or []) if (s := _score(r.get("name") or "", q))]
    scored.sort(key=lambda x: -x[0])  # stabile: a parità resta l'ordine TMDB (popolarità)
    return scored[:limit]


async def _safe(coro) -> dict:
    """Una fonte secondaria che fallisce non deve far fallire la ricerca."""
    try:
        return await coro
    except Exception:
        return {}


async def search_titles(q: str, media_type: str, page: int) -> tuple[list, int]:
    """La ricerca classica per titolo."""
    if media_type == "multi":
        data = await tmdb_get("/search/multi", {"query": q, "page": page})
        # /search/multi restituisce anche le persone: le scartiamo
        results = [
            r for r in data.get("results", [])
            if r.get("media_type") in ("movie", "tv")
        ]
    else:
        data = await tmdb_get(f"/search/{media_type}", {"query": q, "page": page})
        results = data.get("results", [])
        for r in results:
            r["media_type"] = media_type
    return results, min(data.get("total_pages") or 1, _MAX_PAGES)


async def _discover_titles(params: dict, media_type: str, page: int) -> tuple[list, int]:
    """Titoli da /discover (per studio o per keyword), film e serie insieme."""
    types = ("movie", "tv") if media_type == "multi" else (media_type,)
    datas = await asyncio.gather(*[
        _safe(tmdb_get(f"/discover/{t}", {**params, "sort_by": "popularity.desc", "page": page}))
        for t in types
    ])

    results: list = []
    total = 1
    for t, data in zip(types, datas):
        for r in data.get("results", []):
            r["media_type"] = t
            results.append(r)
        total = max(total, min(data.get("total_pages") or 1, _MAX_PAGES))

    results.sort(key=lambda r: r.get("popularity") or 0, reverse=True)
    return results, total


async def _person_titles(person_id: int, media_type: str, page: int) -> tuple[list, int]:
    """Filmografia di una persona: recitata + diretta/scritta, film e serie.

    `combined_credits` arriva tutta in un colpo (non è paginata), quindi la ordiniamo
    per popolarità e la impaginiamo noi.
    """
    data = await _safe(tmdb_get(f"/person/{person_id}/combined_credits", ttl=_ENTITY_TTL))
    wanted = ("movie", "tv") if media_type == "multi" else (media_type,)

    credits = list(data.get("cast") or [])
    credits += [c for c in (data.get("crew") or []) if c.get("job") in _CREW_JOBS]

    seen: set = set()
    items: list = []
    for c in credits:
        key = (c.get("media_type"), c.get("id"))
        if c.get("media_type") not in wanted or key in seen:
            continue  # chi recita e dirige lo stesso film compare due volte
        seen.add(key)
        items.append(c)

    items.sort(key=lambda r: r.get("popularity") or 0, reverse=True)
    total = min(max(1, math.ceil(len(items) / _PAGE_SIZE)), _MAX_PAGES)
    return items[(page - 1) * _PAGE_SIZE: page * _PAGE_SIZE], total


async def smart_search(q: str, media_type: str = "multi", page: int = 1) -> dict:
    """Titoli + filmografie + cataloghi degli studi + temi, in un'unica lista.

    L'ordine è: prima i match sul titolo (è quello che l'utente ha scritto), poi i blocchi
    delle entità riconosciute, dal match più netto al più debole. `matched` serve alla UI
    per dire *perché* stiamo mostrando quei titoli.
    """
    q = q.strip()
    matched = {"people": [], "companies": [], "keywords": []}

    if len(q) < _MIN_QUERY_LEN:
        results, total = await search_titles(q, media_type, page)
        return {"page": page, "results": results, "total_pages": total, "matched": matched}

    titles, people_res, companies_res, keywords_res = await asyncio.gather(
        search_titles(q, media_type, page),
        _safe(tmdb_get("/search/person", {"query": q}, ttl=_ENTITY_TTL)),
        _safe(tmdb_get("/search/company", {"query": q}, ttl=_ENTITY_TTL)),
        _safe(tmdb_get("/search/keyword", {"query": q}, ttl=_ENTITY_TTL)),
    )

    people = _pick(people_res.get("results"), q, 1)
    companies = _pick(companies_res.get("results"), q, _MAX_COMPANIES)
    keywords = _pick(keywords_res.get("results"), q, _MAX_KEYWORDS)

    # Un blocco per fonte: (punteggio, tipo, richiesta dei titoli).
    blocks: list[tuple[int, str, object]] = []
    if people:
        score, p = people[0]
        matched["people"] = [{
            "id": p["id"],
            "name": p.get("name"),
            "profile_path": p.get("profile_path"),
            "known_for_department": p.get("known_for_department"),
        }]
        blocks.append((score, "person", _person_titles(p["id"], media_type, page)))
    if companies:
        matched["companies"] = [
            {"id": c["id"], "name": c.get("name"), "logo_path": c.get("logo_path")}
            for _, c in companies
        ]
        ids = "|".join(str(c["id"]) for _, c in companies)  # '|' = OR su TMDB
        blocks.append((companies[0][0], "company", _discover_titles({"with_companies": ids}, media_type, page)))
    if keywords:
        matched["keywords"] = [{"id": k["id"], "name": k.get("name")} for _, k in keywords]
        ids = "|".join(str(k["id"]) for _, k in keywords)
        blocks.append((keywords[0][0], "keyword", _discover_titles({"with_keywords": ids}, media_type, page)))

    fetched = await asyncio.gather(*[b[2] for b in blocks])

    ordered = sorted(
        zip(blocks, fetched),
        key=lambda bf: (-bf[0][0], _PRIORITY[bf[0][1]]),
    )

    title_results, total = titles
    merged = list(title_results)
    for _block, (block_results, block_total) in ordered:
        merged += block_results
        total = max(total, block_total)

    results: list = []
    seen: set = set()
    for item in merged:
        key = (item.get("media_type"), item.get("id"))
        if key in seen:
            continue  # lo stesso film può arrivare da più fonti
        seen.add(key)
        results.append(item)

    return {"page": page, "results": results, "total_pages": total, "matched": matched}
