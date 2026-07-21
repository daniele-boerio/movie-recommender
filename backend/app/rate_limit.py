"""Rate limiting.

Serve davvero: /auth/register/request spedisce email a indirizzi arbitrari, quindi
senza limiti è un vettore di spam verso terzi (e un modo per far finire in blacklist
il nostro mittente SMTP). /auth/login senza limiti è aperto al brute force.

L'IP del client arriva corretto perché uvicorn gira con --proxy-headers dietro nginx.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# default_limits: rete di sicurezza su TUTTI gli endpoint (via SlowAPIMiddleware in
# main.py), oltre ai limiti più stretti messi a mano su login/registrazione. Generoso,
# così l'uso normale non lo tocca ma uno script che martella l'API viene fermato.
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
