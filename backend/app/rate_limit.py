"""Rate limiting.

Serve davvero: /auth/register/request spedisce email a indirizzi arbitrari, quindi
senza limiti è un vettore di spam verso terzi (e un modo per far finire in blacklist
il nostro mittente SMTP). /auth/login senza limiti è aperto al brute force.

L'IP del client non lo prendiamo da `request.client.host`: con `--proxy-headers` uvicorn
ci mette il *primo* indirizzo di X-Forwarded-For, che lo scrive il client stesso. Bastava
mandare un X-Forwarded-For diverso a ogni tentativo per non incappare mai nel limite.

Qui si legge la catena dal fondo, dove gli indirizzi li aggiungono i nostri proxy:
nginx e Traefik hanno IP privati (rete Docker), quindi il primo indirizzo pubblico da
destra è chi si è collegato davvero a Traefik. Se è un nodo Cloudflare (sito dietro il
proxy di Cloudflare), il client vero sta in CF-Connecting-IP, che Cloudflare sovrascrive
sempre; altrimenti è lui il client. Un CF-Connecting-IP mandato saltando Cloudflare non
conta, perché chi si collega non è un nodo Cloudflare.
"""

import ipaddress

from slowapi import Limiter
from starlette.requests import Request

# https://www.cloudflare.com/ips/ (cambiano di rado)
_CLOUDFLARE_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
        "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
        "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
        "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
        "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
        "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
    )
]


def _parse(ip: str):
    try:
        return ipaddress.ip_address(ip.strip())
    except ValueError:
        return None


def _is_cloudflare(addr) -> bool:
    return any(addr in net for net in _CLOUDFLARE_NETS if net.version == addr.version)


def client_ip(request: Request) -> str:
    """IP del client da usare per i limiti (vedi docstring del modulo)."""
    hops = [h for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    # In fondo c'è anche chi ha parlato col backend (nginx): uvicorn lo mette in client.host
    # solo senza proxy-headers, quindi non lo aggiungiamo, ci basta la catena.
    for raw in reversed(hops):
        addr = _parse(raw)
        if addr is None:
            continue
        if addr.is_private or addr.is_loopback:
            continue  # un nostro proxy (rete Docker): si va oltre
        if _is_cloudflare(addr):
            cf = _parse(request.headers.get("cf-connecting-ip", ""))
            if cf is not None:
                return str(cf)
        return str(addr)
    # Nessun indirizzo pubblico (rete di casa, sviluppo, test): quello della connessione.
    return request.client.host if request.client else "unknown"


# default_limits: rete di sicurezza su TUTTI gli endpoint (via SlowAPIMiddleware in
# main.py), oltre ai limiti più stretti messi a mano su login/registrazione. Generoso,
# così l'uso normale non lo tocca ma uno script che martella l'API viene fermato.
limiter = Limiter(key_func=client_ip, default_limits=["300/minute"])
