"""Registrazione (con verifica email), login, sessione."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth
from ..config import CODE_EXPIRE_MINUTES, CODE_MAX_ATTEMPTS
from ..database import get_db
from ..emailer import send_verification_email
from ..models import EmailVerification, RefreshToken, User
from ..rate_limit import limiter
from ..schemas import LoginRequest, RegisterComplete, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Hash di una password fittizia: fa pagare a un login con utente inesistente lo stesso
# costo bcrypt di uno con utente reale. Senza, il tempo di risposta rivela quali
# account esistono.
_DUMMY_PASSWORD_HASH = auth.get_password_hash("dummy-password-for-timing-safety")

# Messaggio unico per "codice sbagliato", "codice scaduto" e "codice inesistente":
# distinguerli direbbe a un attaccante se un tentativo è sulla strada giusta.
_INVALID_CODE = "Codice non valido o scaduto"


def _issue_session(db: Session, user: User, request: Request, response: Response) -> None:
    """Emette access + refresh token e li mette nei cookie httpOnly."""
    raw_refresh = auth.issue_refresh_token(
        db, user.id, user_agent=request.headers.get("user-agent")
    )
    db.commit()

    auth.set_refresh_cookie(response, raw_refresh)
    auth.set_access_cookie(
        response,
        auth.create_access_token(
            {"user_id": user.id, "token_version": user.token_version}
        ),
    )


@router.post("/register/request")
@limiter.limit("3/hour")
def register_request(
    request: Request,
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Passo 1: genera un codice e lo spedisce all'indirizzo indicato."""
    email = payload.email.lower()

    # Se l'email è già registrata non mandiamo nulla, ma la risposta è identica:
    # altrimenti questo endpoint direbbe a chiunque quali indirizzi hanno un account.
    if not db.query(User).filter(User.email == email).first():
        # Un solo codice valido per volta: i precedenti si bruciano.
        db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.consumed_at.is_(None),
        ).update({"consumed_at": datetime.now(timezone.utc)})

        code = auth.generate_code()
        db.add(
            EmailVerification(
                email=email,
                code_hash=auth.hash_code(code),
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=CODE_EXPIRE_MINUTES),
            )
        )
        db.commit()
        # In background: la risposta non deve aspettare l'SMTP.
        background_tasks.add_task(send_verification_email, email, code)

    return {
        "message": "Se l'indirizzo è valido, riceverai un codice via email.",
        "expires_in_minutes": CODE_EXPIRE_MINUTES,
    }


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/hour")
def register(
    request: Request,
    payload: RegisterComplete,
    response: Response,
    db: Session = Depends(get_db),
):
    """Passo 2: valida il codice e crea l'utente."""
    email = payload.email.lower()
    username = payload.username.lower()

    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.email == email,
            EmailVerification.consumed_at.is_(None),
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    # Il codice vale solo per l'email che l'ha richiesto: è ciò che rende la
    # verifica una verifica. Cercandolo per email, un codice di un altro indirizzo
    # semplicemente non viene trovato.
    if not verification:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_CODE)

    if verification.attempts >= CODE_MAX_ATTEMPTS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Troppi tentativi. Richiedi un nuovo codice.",
        )

    if auth._as_utc(verification.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_CODE)

    if not auth.verify_code(payload.code, verification.code_hash):
        verification.attempts += 1
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _INVALID_CODE)

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email già registrata")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username non disponibile")

    verification.consumed_at = datetime.now(timezone.utc)
    user = User(
        email=email,
        username=username,
        password_hash=auth.get_password_hash(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Due registrazioni in parallelo sullo stesso username/email: il vincolo UNIQUE
        # è l'unico arbitro affidabile, i controlli sopra sono soggetti a race.
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email o username già in uso")
    db.refresh(user)

    _issue_session(db, user, request, response)
    return user


@router.post("/login", response_model=UserResponse)
@limiter.limit("10/minute;50/hour")
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    identifier = payload.identifier.lower().strip()

    user = (
        db.query(User)
        .filter(or_(User.username == identifier, User.email == identifier))
        .first()
    )

    # Utente inesistente e password errata devono essere indistinguibili, nel messaggio
    # e nel tempo di risposta: altrimenti /login diventa un oracolo per scoprire
    # quali account esistono. Se l'utente non c'è, paghiamo comunque un bcrypt.
    if user:
        password_ok = auth.verify_password(payload.password, user.password_hash)
    else:
        auth.verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        password_ok = False

    if not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenziali non valide")

    _issue_session(db, user, request, response)
    return user


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    """Ruota il refresh token ed emette un nuovo access token."""
    raw_token = request.cookies.get(auth.REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessione assente")

    db_token = auth.consume_refresh_token(db, raw_token)

    user = db.get(User, db_token.user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessione non valida")

    # Stessa famiglia: il nuovo token resta nella catena del precedente.
    new_raw = auth.issue_refresh_token(
        db,
        user.id,
        user_agent=request.headers.get("user-agent"),
        family_id=db_token.family_id,
    )
    db.commit()

    auth.set_refresh_cookie(response, new_raw)
    auth.set_access_cookie(
        response,
        auth.create_access_token(
            {"user_id": user.id, "token_version": user.token_version}
        ),
    )
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(auth.REFRESH_COOKIE_NAME)
    if raw_token:
        auth.revoke_session(db, raw_token)
        db.commit()
    auth.clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(auth.get_current_user_id),
):
    user = db.get(User, current_user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Non autenticato")
    return user


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(auth.get_current_user_id),
):
    """Sessioni attive dell'utente (utile per accorgersi di accessi non propri)."""
    rows = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == current_user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .order_by(RefreshToken.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "user_agent": r.user_agent,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_used_at": r.used_at.isoformat() if r.used_at else None,
        }
        for r in rows
    ]
