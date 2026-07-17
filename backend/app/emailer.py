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


def send_verification_email(email_to: str, code: str) -> None:
    if not SMTP_SERVER or not SMTP_USERNAME or not SMTP_PASSWORD:
        # Mock di sviluppo: si testa tutto il flusso senza un SMTP vero.
        logger.warning(
            "SMTP non configurato: email di verifica SIMULATA (MOCK) per %s. Codice: %s",
            email_to,
            code,
        )
        return

    try:
        msg = EmailMessage()
        msg.set_content(
            f"Ciao,\n\n"
            f"Il tuo codice per completare la registrazione su WatchNext è:\n\n"
            f"    {code}\n\n"
            f"Scade tra {CODE_EXPIRE_MINUTES} minuti.\n\n"
            f"Se non hai richiesto tu la registrazione, ignora questa email."
        )
        msg["Subject"] = "Il tuo codice di verifica WatchNext"
        msg["From"] = EMAIL_FROM
        msg["To"] = email_to

        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email di verifica inviata a %s", email_to)
    except Exception as e:
        # L'invio gira in background: se fallisce lo logghiamo, ma non c'è nessuna
        # risposta HTTP da far fallire a questo punto.
        logger.error("Errore durante l'invio dell'email a %s: %s", email_to, e)
