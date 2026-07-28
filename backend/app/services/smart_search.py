"""Ricerca "intelligente": non solo titoli, ma anche persone, studi e temi.

Cercare `marvel` deve dare i film Marvel, `disney` quelli Disney, `nolan` i film di
Nolan, `zombie` i film di zombie — non solo i titoli che contengono quella parola. Per
farlo, oltre alla ricerca per titolo interroghiamo `/search/person`, `/search/company` e
`/search/keyword`: per le entità che corrispondono *davvero* alla query tiriamo giù i
titoli collegati e li accodiamo ai risultati per titolo.

I filtri (genere, anno, voto, lingua) e l'ordinamento si applicano **qui**, non nel
frontend. Filtrare lato client la singola pagina lasciava passare tutto il resto: la
pagina 2 poteva contenere titoli più vecchi della 1 e le pagine si svuotavano man mano
che il filtro scartava roba. Vedi `SearchFilters` e la "modalità profonda" più sotto.

Tutte le chiamate passano da `tmdb_get`, quindi sono in cache: la stessa query digitata
da un altro utente (o la pagina 2 chiesta subito dopo) non ricontatta TMDB.
"""

import asyncio
import math
import unicodedata
from dataclasses import dataclass

from ..tmdb import tmdb_get

_PAGE_SIZE = 20      # dimensione pagina di TMDB
_MAX_PAGES = 500     # oltre la 500 TMDB dà errore
_MIN_QUERY_LEN = 3   # sotto i 3 caratteri l'espansione è solo rumore (e ~8 chiamate)
_ENTITY_TTL = 21600  # 6h: persone, studi e keyword non cambiano quasi mai

# "disney" pesca Walt Disney Pictures, Walt Disney Animation Studios, Disney Channel,
# Disneynature… e i film stanno sparsi tra tutte: le prendiamo tutte, tanto finiscono
# in un'unica chiamata a /discover con gli id in OR.
_MAX_COMPANIES = 8
_MAX_KEYWORDS = 2

# Modalità profonda: con filtri o ordinamento attivi non basta impaginare fonte per
# fonte. Tiriamo giù più pagine per fonte, filtriamo e ordiniamo tutto insieme, e
# impaginiamo *quello*: così "carica altri" prosegue la stessa classifica invece di
# ricominciarne una nuova.
_POOL_PAGES = 3
_POOL_PAGE_SIZE = 40

# Ruoli di troupe che rendono un titolo "di" quella persona. Niente produttori o
# reparti tecnici: cercando un regista si vogliono i suoi film, non tutti quelli
# in cui compare nei titoli di coda.
_CREW_JOBS = {"Director", "Series Director", "Writer", "Screenplay", "Story", "Creator"}

# Ordine dei blocchi a parità di punteggio: un nome-marchio è quasi sempre lo studio.
_PRIORITY = {"company": 0, "keyword": 1, "person": 2}

# Ordinando per voto serve una soglia di votanti, o un titolo con 1 solo voto a 10 svetta.
_VOTE_COUNT_FLOOR = 50

SORTS = ("relevance", "popularity.desc", "vote_average.desc", "date.desc")


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


def _pick(results: list | None, q: str, limit: int, *, keep_order: bool = False) -> list[tuple[int, dict]]:
    """Le entità che corrispondono alla query, dalla più pertinente.

    `keep_order` tiene l'ordine di TMDB invece del nostro punteggio: per gli studi è
    quello giusto, perché "Walt Disney Pictures" (la query è un pezzo del nome) vale
    quanto "Disney Channel" (il nome comincia con la query) ma vale molto di più per
    l'utente — e TMDB questo lo sa già.
    """
    scored = [(s, r) for r in (results or []) if (s := _score(r.get("name") or "", q))]
    if not keep_order:
        scored.sort(key=lambda x: -x[0])  # stabile: a parità resta l'ordine TMDB
    return scored[:limit]


def _date_of(item: dict) -> str:
    return item.get("release_date") or item.get("first_air_date") or ""


def _year_of(item: dict) -> int | None:
    head = _date_of(item)[:4]
    return int(head) if head.isdigit() else None


@dataclass(frozen=True)
class SearchFilters:
    """Cosa deve rispettare un risultato, e in che ordine mostrarlo."""

    genres: frozenset[int] = frozenset()
    year_from: int | None = None
    year_to: int | None = None
    vote_min: float = 0.0
    original_language: str | None = None   # 'ja' per gli anime
    sort_by: str = "relevance"

    @classmethod
    def from_query(
        cls,
        genres: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        vote_min: float = 0.0,
        original_language: str | None = None,
        sort_by: str = "relevance",
    ) -> "SearchFilters":
        ids = frozenset(
            int(p) for p in (genres or "").split(",") if p.strip().lstrip("-").isdigit()
        )
        return cls(
            genres=ids,
            year_from=year_from,
            year_to=year_to,
            vote_min=vote_min,
            original_language=original_language,
            sort_by=sort_by if sort_by in SORTS else "relevance",
        )

    @property
    def active(self) -> bool:
        """Se è attivo qualcosa serve la modalità profonda."""
        return bool(
            self.genres
            or self.year_from
            or self.year_to
            or self.vote_min
            or self.original_language
            or self.sort_by != "relevance"
        )

    def accepts(self, item: dict) -> bool:
        """Il filtro applicato a mano, per le fonti che TMDB non sa filtrare da sé."""
        if self.genres and not (set(item.get("genre_ids") or []) & self.genres):
            return False
        if self.original_language and item.get("original_language") != self.original_language:
            return False
        if self.vote_min and (item.get("vote_average") or 0) < self.vote_min:
            return False

        if self.year_from or self.year_to:
            year = _year_of(item)
            if year is None:
                return False  # senza data non possiamo dire che rispetti l'intervallo
            if self.year_from and year < self.year_from:
                return False
            if self.year_to and year > self.year_to:
                return False
        return True

    def discover_params(self, media_type: str) -> dict:
        """Gli stessi filtri detti a TMDB, che li applica meglio di noi: /discover li
        usa per selezionare *e* impaginare, quindi le pagine arrivano già piene."""
        date_field = "first_air_date" if media_type == "tv" else "primary_release_date"
        params: dict = {"sort_by": self._tmdb_sort(date_field)}

        if self.genres:
            params["with_genres"] = "|".join(str(g) for g in sorted(self.genres))  # '|' = OR
        if self.original_language:
            params["with_original_language"] = self.original_language
        if self.vote_min:
            params["vote_average.gte"] = self.vote_min
        if self.vote_min or self.sort_by == "vote_average.desc":
            params["vote_count.gte"] = _VOTE_COUNT_FLOOR
        if self.year_from:
            params[f"{date_field}.gte"] = f"{self.year_from}-01-01"
        if self.year_to:
            params[f"{date_field}.lte"] = f"{self.year_to}-12-31"
        return params

    def _tmdb_sort(self, date_field: str) -> str:
        if self.sort_by == "date.desc":
            return f"{date_field}.desc"
        if self.sort_by == "vote_average.desc":
            return "vote_average.desc"
        return "popularity.desc"  # anche per "relevance": è l'ordine naturale di discover

    def sorted_pool(self, items: list) -> list:
        """L'ordinamento globale, sull'intero serbatoio e non pagina per pagina."""
        if self.sort_by == "date.desc":
            return sorted(items, key=_date_of, reverse=True)  # senza data → in fondo
        if self.sort_by == "vote_average.desc":
            return sorted(items, key=lambda it: it.get("vote_average") or 0, reverse=True)
        if self.sort_by == "popularity.desc":
            return sorted(items, key=lambda it: it.get("popularity") or 0, reverse=True)
        return items  # relevance: l'ordine con cui abbiamo unito le fonti è già quello


async def _safe(coro) -> dict:
    """Una fonte secondaria che fallisce non deve far fallire la ricerca."""
    try:
        return await coro
    except Exception:
        return {}


async def search_titles(q: str, media_type: str, pages: list[int]) -> tuple[list, int]:
    """La ricerca classica per titolo, su una o più pagine."""
    path = "/search/multi" if media_type == "multi" else f"/search/{media_type}"
    datas = await asyncio.gather(*[_safe(tmdb_get(path, {"query": q, "page": p})) for p in pages])

    results: list = []
    total = 1
    for data in datas:
        for r in data.get("results", []):
            if media_type == "multi":
                # /search/multi restituisce anche le persone: le scartiamo
                if r.get("media_type") not in ("movie", "tv"):
                    continue
            else:
                r["media_type"] = media_type
            results.append(r)
        total = max(total, min(data.get("total_pages") or 1, _MAX_PAGES))
    return results, total


async def _discover_titles(
    base: dict, media_type: str, pages: list[int], filters: SearchFilters
) -> tuple[list, int]:
    """Titoli da /discover (per studio o per keyword), film e serie insieme."""
    types = ("movie", "tv") if media_type == "multi" else (media_type,)
    jobs = [
        (t, p, _safe(tmdb_get(f"/discover/{t}", {**base, **filters.discover_params(t), "page": p})))
        for t in types
        for p in pages
    ]
    datas = await asyncio.gather(*[j[2] for j in jobs])

    results: list = []
    total = 1
    for (t, _p, _c), data in zip(jobs, datas):
        for r in data.get("results", []):
            r["media_type"] = t
            results.append(r)
        total = max(total, min(data.get("total_pages") or 1, _MAX_PAGES))

    results.sort(key=lambda r: r.get("popularity") or 0, reverse=True)
    return results, total


async def _person_titles(
    person_id: int, media_type: str, pages: list[int], deep: bool
) -> tuple[list, int]:
    """Filmografia di una persona: recitata + diretta/scritta, film e serie.

    `combined_credits` arriva tutta in un colpo (non è paginata): in modalità profonda
    la restituiamo intera e ci pensa il serbatoio a filtrarla e ordinarla, altrimenti
    la impaginiamo noi per popolarità.
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
    if deep:
        return items, 1

    page = pages[0]
    total = min(max(1, math.ceil(len(items) / _PAGE_SIZE)), _MAX_PAGES)
    return items[(page - 1) * _PAGE_SIZE: page * _PAGE_SIZE], total


def _dedupe(items: list) -> list:
    out: list = []
    seen: set = set()
    for item in items:
        key = (item.get("media_type"), item.get("id"))
        if key in seen:
            continue  # lo stesso film può arrivare da più fonti
        seen.add(key)
        out.append(item)
    return out


async def smart_search(
    q: str,
    media_type: str = "multi",
    page: int = 1,
    filters: SearchFilters | None = None,
) -> dict:
    """Titoli + filmografie + cataloghi degli studi + temi, in un'unica lista.

    L'ordine è: prima i match sul titolo (è quello che l'utente ha scritto), poi i blocchi
    delle entità riconosciute, dal match più netto al più debole. `matched` serve alla UI
    per dire *perché* stiamo mostrando quei titoli.
    """
    q = q.strip()
    filters = filters or SearchFilters()
    deep = filters.active
    matched = {"people": [], "companies": [], "keywords": []}

    # Con i filtri attivi serve un serbatoio più profondo da ordinare tutto insieme.
    pages = list(range(1, _POOL_PAGES + 1)) if deep else [page]

    if len(q) < _MIN_QUERY_LEN:
        results, total = await search_titles(q, media_type, pages)
        if deep:
            results = filters.sorted_pool([r for r in results if filters.accepts(r)])
            return _paginate(results, page, matched)
        return {"page": page, "results": results, "total_pages": total, "matched": matched}

    titles, people_res, companies_res, keywords_res = await asyncio.gather(
        search_titles(q, media_type, pages),
        _safe(tmdb_get("/search/person", {"query": q}, ttl=_ENTITY_TTL)),
        _safe(tmdb_get("/search/company", {"query": q}, ttl=_ENTITY_TTL)),
        _safe(tmdb_get("/search/keyword", {"query": q}, ttl=_ENTITY_TTL)),
    )

    people = _pick(people_res.get("results"), q, 1)
    companies = _pick(companies_res.get("results"), q, _MAX_COMPANIES, keep_order=True)
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
        blocks.append((score, "person", _person_titles(p["id"], media_type, pages, deep)))
    if companies:
        matched["companies"] = [
            {"id": c["id"], "name": c.get("name"), "logo_path": c.get("logo_path")}
            for _, c in companies
        ]
        ids = "|".join(str(c["id"]) for _, c in companies)  # '|' = OR su TMDB
        blocks.append((
            max(s for s, _ in companies),
            "company",
            _discover_titles({"with_companies": ids}, media_type, pages, filters),
        ))
    if keywords:
        matched["keywords"] = [{"id": k["id"], "name": k.get("name")} for _, k in keywords]
        ids = "|".join(str(k["id"]) for _, k in keywords)
        blocks.append((
            max(s for s, _ in keywords),
            "keyword",
            _discover_titles({"with_keywords": ids}, media_type, pages, filters),
        ))

    fetched = await asyncio.gather(*[b[2] for b in blocks])
    ordered = sorted(zip(blocks, fetched), key=lambda bf: (-bf[0][0], _PRIORITY[bf[0][1]]))

    title_results, total = titles
    merged = list(title_results)
    for _block, (block_results, block_total) in ordered:
        merged += block_results
        total = max(total, block_total)

    if deep:
        # Il filtro passa su tutto, comprese le fonti che TMDB ha già filtrato: è quello
        # che rende vera la promessa "filtrato vuol dire filtrato".
        pool = filters.sorted_pool(_dedupe([r for r in merged if filters.accepts(r)]))
        return _paginate(pool, page, matched)

    return {"page": page, "results": _dedupe(merged), "total_pages": total, "matched": matched}


def _paginate(pool: list, page: int, matched: dict) -> dict:
    """Impagina il serbatoio già filtrato e ordinato: `total_pages` è quello vero, non
    quello di TMDB, così "carica altri" sparisce quando i risultati sono finiti."""
    total = max(1, math.ceil(len(pool) / _POOL_PAGE_SIZE))
    start = (page - 1) * _POOL_PAGE_SIZE
    return {
        "page": page,
        "results": pool[start: start + _POOL_PAGE_SIZE],
        "total_pages": total,
        "matched": matched,
    }
