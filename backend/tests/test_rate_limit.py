"""Chiave del rate limit: l'IP vero del client, non quello che il client dichiara."""

from starlette.requests import Request

from app.rate_limit import client_ip


def _req(xff=None, cf=None, host="172.18.0.5"):
    headers = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    if cf is not None:
        headers.append((b"cf-connecting-ip", cf.encode()))
    return Request({"type": "http", "headers": headers, "client": (host, 1234)})


def test_x_forwarded_for_falsificato_non_conta():
    # Il client manda "1.2.3.4"; Traefik aggiunge chi si è collegato (8.8.8.8), nginx il suo.
    assert client_ip(_req("1.2.3.4, 8.8.8.8, 172.18.0.2")) == "8.8.8.8"


def test_dietro_cloudflare_vale_cf_connecting_ip():
    assert client_ip(_req("5.6.7.8, 172.71.144.57, 172.18.0.2", cf="5.6.7.8")) == "5.6.7.8"


def test_cf_connecting_ip_senza_cloudflare_ignorato():
    # Chi salta Cloudflare e si inventa l'header resta identificato col suo IP.
    assert client_ip(_req("8.8.8.8, 172.18.0.2", cf="9.9.9.9")) == "8.8.8.8"


def test_senza_ip_pubblici_usa_la_connessione():
    assert client_ip(_req(None, host="127.0.0.1")) == "127.0.0.1"
