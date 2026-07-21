"""Invio email. Senza SMTP configurato l'email viene loggata invece che spedita."""

import logging
import smtplib
from email.message import EmailMessage

from .config import (
    CODE_EXPIRE_MINUTES,
    EMAIL_FROM,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USERNAME,
)

logger = logging.getLogger(__name__)


def _deliver(email_to: str, subject: str, body: str) -> None:
    """Spedisce una mail, o la logga se l'SMTP non è configurato.

    Il body finisce nei log nel caso mock: è il modo in cui in sviluppo si legge il
    codice (niente SMTP → il codice si prende dai log del backend)."""
    if not SMTP_SERVER or not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning(
            "SMTP non configurato: email SIMULATA (MOCK) per %s.\n[%s]\n%s",
            email_to,
            subject,
            body,
        )
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = email_to

        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email inviata a %s (%s)", email_to, subject)
    except Exception as e:
        # L'invio gira in background: se fallisce lo logghiamo, ma non c'è nessuna
        # risposta HTTP da far fallire a questo punto.
        logger.error("Errore durante l'invio dell'email a %s: %s", email_to, e)


def send_verification_email(email_to: str, code: str) -> None:
    _deliver(
        email_to,
        "Il tuo codice di verifica WatchNext",
        f"Ciao,\n\n"
        f"Il tuo codice per completare la registrazione su WatchNext è:\n\n"
        f"    {code}\n\n"
        f"Scade tra {CODE_EXPIRE_MINUTES} minuti.\n\n"
        f"Se non hai richiesto tu la registrazione, ignora questa email.",
    )


def send_email_change_email(email_to: str, code: str) -> None:
    _deliver(
        email_to,
        "Conferma il tuo nuovo indirizzo WatchNext",
        f"Ciao,\n\n"
        f"Hai chiesto di collegare questo indirizzo al tuo account WatchNext.\n"
        f"Il codice di conferma è:\n\n"
        f"    {code}\n\n"
        f"Scade tra {CODE_EXPIRE_MINUTES} minuti.\n\n"
        f"Se non sei stato tu, ignora questa email: il tuo account resta invariato.",
    )
