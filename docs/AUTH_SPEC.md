# PharmaCare — Authentication API Specification (AUTH_SPEC)

**Project:** PharmaCare — AI-powered pharma complaint management system (AIVOA Round 1 AI Product Engineer assessment)
**Scope:** Remove the "no user auth (single-tenant demo scope)" stub from README; add JWT-based authentication to the FastAPI backend + contract for the React SPA.
**Status:** Implementation-ready specification. No code changes were made by this document; implementers follow the checklist in §13.
**Date:** 2026-08-08

---

## 1. Decision Summary (read this first)

| Decision | Choice | Rationale (short) |
|---|---|---|
| Token model | **JWT access tokens** (stateless) | React SPA talks to a single FastAPI backend over `/api` proxy; JWT needs no server-side session store, works out of the box with Swagger "Authorize", and is the standard for demo-scope SaaS. Opaque tokens/sessions require a store + cookie/CSRF plumbing that buys nothing at this scale. |
| Access token expiry | **60 minutes** | Short enough to limit stolen-token window, long enough that a demo doesn't hit mid-presentation logouts. Frontend refreshes proactively (§12). |
| Refresh token | **Yes — short-lived, stateless, NO rotation** (7 days) | Rotation requires server-side state (denylist/version table) and race handling. A 7-day stateless JWT refresh gives the demo persistent sessions with a bounded blast radius and zero new tables. Trade-off documented in §3.3. |
| Logout endpoint | **No endpoint — client-side token drop** | JWT is stateless; the server cannot revoke. A `/logout` endpoint would be a no-op. Client discards tokens (§12). Documented, not built. |
| Password hashing | **passlib 1.7.4 + bcrypt (pinned `bcrypt==4.0.1`)** | OWASP-acceptable, battle-tested, integrates with passlib out of the box. Argon2 rejected: passlib's argon2 support is stale/buggy with current `argon2-cffi`, and argon2 adds native deps for zero demo benefit. **Pin is critical — see §4.1.** |
| JWT library | **PyJWT (`PyJWT==2.10.1`)** | Actively maintained, pure Python, zero deps. `python-jose` is unmaintained since 2021 and has published CVEs (CVE-2024-33663/33664). |
| Login request format | **`OAuth2PasswordRequestForm` (form-encoded `username`/`password`)** | Makes Swagger "Authorize" button work for free. Requires `python-multipart` — **already in `requirements.txt` (0.0.20), do not re-add**. |
| Role at registration | **Not settable — always `analyst`** | Prevents self-escalation. Admin promotion happens in DB/seed (§11.3). |
| Route protection | **Router-level `Depends(get_current_user)` on all `/api/complaints*` and `/api/ai/*`; `/api/auth/*`, `/`, `/health` open** | Protect the whole domain by default; auth endpoints must stay open (bootstrap). |
| Email field in login form | `username` carries the **email address** | OAuth2 convention; frontend must send the email in the `username` field (§12). |

---

## 2. Auth Model & Token Design

### 2.1 Why JWT (vs opaque tokens / server sessions)

- **Stateless**: the backend stores nothing per session → zero new tables (besides `users`), trivially works on the existing SQLite-fallback deployment.
- **Demo-appropriate**: a single backend, no microservice fan-out, no need for shared session stores or cookie/CSRF handling.
- **Tooling**: `OAuth2PasswordBearer` + `OAuth2PasswordRequestForm` give the Swagger UI "Authorize" flow for free, which the demo script relies on.
- Trade-offs accepted: no server-side revocation (mitigated by short expiry + short-lived refresh), token size overhead (~400 bytes, irrelevant here).

### 2.2 Token payloads (exact claims)

Both token types are HS256 JWTs signed with `settings.jwt_secret`. The `type` claim prevents a refresh token being used as an access token and vice versa.

**Access token** (lifetime `access_token_expire_minutes`, default 60 min):

```json
{
  "sub": "3f2c8b1e-9a4d-4f6e-8b1c-2d3e4f5a6b7c",   // user.id (UUID string)
  "type": "access",
  "iat": 1783500000,
  "exp": 1783503600
}
```

**Refresh token** (lifetime `refresh_token_expire_days`, default 7 days):

```json
{
  "sub": "3f2c8b1e-9a4d-4f6e-8b1c-2d3e4f5a6b7c",
  "type": "refresh",
  "iat": 1783500000,
  "exp": 1784104800
}
```

Notes:
- `sub` must be a **string** (PyJWT 2.10 warns/errors on non-string `sub`). Our `User.id` is a `String(36)` UUID — no conversion needed.
- Use `datetime.now(timezone.utc)` for `iat`/`exp` (Python 3.11). PyJWT accepts `datetime` for `exp` and converts.
- Do **not** put email, role, or password data in the token. Role changes must be live-read from DB by `get_current_user` (§7).

### 2.3 Refresh semantics (no rotation — read carefully)

- `/api/auth/refresh` validates the refresh JWT (signature, `type == "refresh"`, expiry) and the user's existence + `is_active`, then issues a **new access token**.
- The refresh token itself is **not rotated** and **not stored server-side**. It remains valid until its `exp` (7 days from issue) or until the user is deactivated/deleted.
- Accepted trade-off: a stolen refresh token works until expiry. Mitigation for the demo: 7-day window, `is_active` check on every refresh, and documented upgrade path (rotation via a `token_jti` denylist table or a `token_version` column on `users`) if this product outlives the assessment.
- If refresh fails (expired/invalid/inactive) → `401` → client must force re-login (§12).

### 2.4 Login / token response shape

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "<jwt>"
}
```

`expires_in` is the access token TTL in seconds (useful for the frontend to schedule proactive refresh). `refresh_token` is returned by **login only** (refresh returns a new access token without a new refresh token).

---

## 3. Dependencies (exact pins — add to `backend/requirements.txt`)

```text
# --- Auth ---
passlib==1.7.4
bcrypt==4.0.1          # MUST stay <4.1 — see pitfall below
PyJWT==2.10.1
email-validator==2.2.0 # required by pydantic v2 EmailStr
```

Already present, do not duplicate: `python-multipart==0.0.20` (required by `OAuth2PasswordRequestForm`).

### 3.1 ⚠️ The passlib/bcrypt version trap (known pitfall)

`passlib 1.7.4` (the final release — the library is unmaintained) imports `bcrypt.__about__.__version__` internally. **`bcrypt 4.1+` removed the `__about__` module**, so `passlib` crashes at hash time with:

```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**Do not** `pip install bcrypt` unpinned, and do **not** let pip resolve "latest" (by 2026 that means bcrypt 5.x — also broken). The safe combination is:

```text
passlib==1.7.4 + bcrypt==4.0.1
```

- `bcrypt==4.0.1` ships Windows `cp311` wheels — no build tools needed.
- Verify after install: `python -c "from passlib.hash import bcrypt; print(bcrypt.hash('x'))"` — if this raises `AttributeError: __about__`, the pin was lost (someone installed `bcrypt>=4.1`); fix with `pip install "bcrypt==4.0.1"`.

**Fallback if lead-dev prefers to skip passlib entirely** (documented alternative, not the primary choice): call `bcrypt` directly —

```python
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
ok = bcrypt.checkpw(password.encode(), hashed.encode())
```

### 3.2 Why PyJWT over python-jose

`python-jose` (last release 2021) is unmaintained and has disclosed signature/algorithm-handling CVEs; PyJWT is actively maintained, pure Python, and its API for our use (`jwt.encode/decode` with `algorithms=[...]`) is simpler.

### 3.3 Argon2 — rejected, with reason

Argon2 is technically the strongest PHC-winner and OWASP-listed, but:
- passlib's argon2 handler is known to break against recent `argon2-cffi` releases (same class of problem as the bcrypt issue, less documented).
- Adds a native dependency for no observable benefit in a demo.
- bcrypt with cost 12 (§10) is fully acceptable for this threat model.

If the team ever upgrades, prefer `argon2-cffi` used directly (never through passlib).

---

## 4. User Model

### 4.1 `backend/app/models/user.py`

Follow the exact style of `app/models/complaint.py` (Mapped columns, `gen_uuid`, String-typed enums). **No `Enum` column type — SQLite (the fallback DB) does not support native ENUMs; the codebase already stores enum *values* in `String` columns (`complaints.status`), keep that pattern.**

```python
"""User model for authentication and role-based access."""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.complaint import gen_uuid


class UserRole(str, enum.Enum):
    ANALYST = "analyst"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.ANALYST.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

Field rationale:

| Field | Type / constraint | Why |
|---|---|---|
| `id` | `String(36)`, PK, `default=gen_uuid` | Matches `complaints.id` pattern; string UUID avoids native-UUID drift between Postgres/SQLite. |
| `email` | `String(255)`, `unique=True`, `index=True` | Unique login identity; 255 covers RFC max. |
| `hashed_password` | `String(255)` | bcrypt hashes are 60 chars; 255 gives headroom for future algorithm swaps. |
| `full_name` | `String(200)`, not null | Display name; matches the 200-char convention used elsewhere. |
| `role` | `String(20)`, default `"analyst"` | Values `analyst` \| `admin`. **String, not Enum column** (SQLite). Code-side enum `UserRole` keeps type safety. |
| `is_active` | `Boolean`, default `True` | Soft-deactivation: refresh + every request rejects inactive users. |
| `created_at` / `updated_at` | `DateTime`, Python-side defaults | Identical convention to `Complaint` (Python-side `default=`/`onupdate=`, no `server_default` — keeps the migration portable across Postgres and SQLite). |

Register `User` in `app/models/__init__.py`:

```python
from app.models.complaint import Complaint, StatusHistory
from app.models.user import User, UserRole

__all__ = ["Complaint", "StatusHistory", "User", "UserRole"]
```

### 4.2 Pydantic schemas (`app/schemas/auth.py`)

```python
"""Pydantic schemas for authentication."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)  # 72 = bcrypt input limit

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, v):
        return v.strip() if isinstance(v, str) else v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: Literal["analyst", "admin"]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None   # present on login; null on refresh


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)
```

Notes:
- `email` uses `EmailStr` → requires the `email-validator` pin (§3).
- **No `role` field in `UserCreate`** — role is server-assigned `analyst` at registration. Self-escalation is impossible by construction.
- `password` max 72 **characters**: bcrypt silently truncates input at 72 **bytes**; capping at 72 chars avoids hash-collision surprises entirely. (Non-ASCII multi-byte input at exactly 72 chars can still exceed 72 bytes — acceptable for demo; note in §10.)

---

## 5. Settings Changes

### 5.1 `backend/app/config.py` — add to `Settings`

```python
# --- Auth / JWT ---
jwt_secret: str = "dev-only-insecure-secret-change-in-env-0f1f2e3d4c5b6a7988"
jwt_algorithm: str = "HS256"
access_token_expire_minutes: int = 60
refresh_token_expire_days: int = 7
```

Rules (non-negotiable):
1. **`JWT_SECRET` must come from `.env` in any shared/production-ish environment.** The dev default above is a *fixed* literal (never `secrets.token_urlsafe()` at boot — a random-per-boot secret silently logs everyone out on every restart).
2. `pydantic-settings` maps field `jwt_secret` ↔ env var `JWT_SECRET` automatically (case-insensitive) — no extra code.
3. Generate a real secret with: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
4. **Rotating `JWT_SECRET` invalidates every outstanding access and refresh token** — plan demo restarts accordingly.

### 5.2 `backend/.env.example` — append

```text
# --- Auth / JWT ---
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
# REQUIRED in production. Dev default exists in config.py but is insecure.
JWT_SECRET=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## 6. Endpoints (OpenAPI-style contracts)

Router: `app/api/auth.py`, `APIRouter(prefix="/api/auth", tags=["auth"])`.

**Error shape** (unified with the existing codebase — `complaints.py` raises `HTTPException(status_code=..., detail="...")`): every error is `{"detail": "<message>"}`. 422 validation errors keep FastAPI's default shape (§9). All auth 401s additionally set header `WWW-Authenticate: Bearer`.

---

### 6.1 POST `/api/auth/register` — open, 201

Creates an analyst account. **Role is not accepted** — always `"analyst"`.

Request (`application/json`):

```json
{
  "full_name": "Jane Analyst",
  "email": "  Jane.Analyst@PharmaCare.Dev  ",
  "password": "correct-horse-battery"
}
```

Response `201` (`application/json`) — the created user, **no token** (client proceeds to login; keeps register/login contracts independent and predictable):

```json
{
  "id": "3f2c8b1e-9a4d-4f6e-8b1c-2d3e4f5a6b7c",
  "email": "jane.analyst@pharmacare.dev",
  "full_name": "Jane Analyst",
  "role": "analyst",
  "is_active": true,
  "created_at": "2026-08-08T09:15:00Z",
  "updated_at": "2026-08-08T09:15:00Z"
}
```

Errors:

| Status | Body `detail` | Trigger |
|---|---|---|
| 409 | `"Email already registered"` | Email (normalized) exists — check case-insensitively *after* lowercase normalization |
| 422 | FastAPI default validation shape | Missing/short password, invalid email, empty name |

Notes:
- Email normalization happens in the schema validator (lowercase + strip) and again defensively in `crud/user.py::create_user`.
- Consider a light startup-rate limit on this open endpoint in the future (§10.6).

---

### 6.2 POST `/api/auth/login` — open, 200

**`OAuth2PasswordRequestForm`** (body must be `application/x-www-form-urlencoded`, fields `username` + `password`). `username` carries the **email** (case-insensitive). This is what powers the Swagger "Authorize" button via `OAuth2PasswordBearer(tokenUrl="/api/auth/login")`.

Request (`application/x-www-form-urlencoded`):

```
username=jane.analyst@pharmacare.dev&password=correct-horse-battery
```

Response `200`:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzZjJjOGIxZS05YTQ0ZTRmNi04YjFjLTJkM2U0ZjVhNmI3YyIsInR5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3ODM1MDAwMDAsImV4cCI6MTc4MzUwMzYwMH0.sig",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzZjJjOGIxZS05YTQ0ZTRmNi04YjFjLTJkM2U0ZjVhNmI3YyIsInR5cGUiOiJyZWZyZXNoIiwiaWF0IjoxNzgzNTAwMDAwLCJleHAiOjE3ODQxMDQ4MDB9.sig"
}
```

Errors:

| Status | Body `detail` | Trigger |
|---|---|---|
| 401 | `"Incorrect email or password"` | Unknown email **or** wrong password — **identical message** for both, no user enumeration |
| 401 | `"Account is disabled"` | `is_active == False` |
| 422 | validation shape | Missing form fields |

Implementation notes:
- bcrypt `verify` cost ≈ 0.2–0.3 s at rounds=12 — expected, do not treat as a hang.
- Normalize `username` (strip/lower) before lookup.

---

### 6.3 GET `/api/auth/me` — protected, 200

Current user from the access token. Uses `Depends(get_current_user)`.

Request: `Authorization: Bearer <access_token>` (no body).

Response `200` — `UserOut` (same shape as register response).

Errors:

| Status | Body `detail` | Trigger |
|---|---|---|
| 401 | `"Token has expired"` | `ExpiredSignatureError` (frontend should then attempt refresh, §12) |
| 401 | `"Could not validate credentials"` | Malformed/forged token, wrong type, unknown user, or inactive user |
| 401 | — | Missing `Authorization` header (raised by `OAuth2PasswordBearer` itself; also carries `WWW-Authenticate`) |

---

### 6.4 POST `/api/auth/refresh` — open, 200

Exchanges a valid refresh token for a **new access token**. Refresh token is not rotated (§2.3).

Request (`application/json`):

```json
{ "refresh_token": "<refresh jwt>" }
```

Response `200` — `refresh_token` is `null` here:

```json
{
  "access_token": "<new access jwt>",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": null
}
```

Errors:

| Status | Body `detail` | Trigger |
|---|---|---|
| 401 | `"Invalid refresh token"` | Signature/format/type mismatch |
| 401 | `"Refresh token expired"` | `ExpiredSignatureError` → client must re-login |
| 401 | `"Account is disabled"` | User inactive/deleted |

---

### 6.5 POST `/api/auth/logout` — **not implemented (by design)**

Stateless JWTs cannot be revoked server-side; a logout endpoint would be a documented no-op. **Client-side logout contract:** frontend discards `access_token` + `refresh_token`, resets auth state, redirects to `/login`. Documented here so the designer doesn't build against a phantom endpoint. (Upgrade path if revocation is ever needed: `token_version` column or jti denylist — see §2.3.)

---

## 7. Protection Strategy

### 7.1 Security module — `app/security.py`

```python
"""Password hashing and JWT creation/validation."""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # rounds=12 (bcrypt default)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(sub: str, token_type: str, ttl_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, "access", settings.access_token_expire_minutes)


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, "refresh", settings.refresh_token_expire_days * 24 * 60)
```

### 7.2 Dependency — `app/api/deps.py`

```python
"""Shared FastAPI dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import jwt

from app.config import get_settings
from app.crud.user import get_user_by_id
from app.database import get_db
from app.models.user import User

settings = get_settings()

# Must match the login path exactly for Swagger "Authorize" to work.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            raise _UNAUTHORIZED
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise _UNAUTHORIZED from None

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    return user
```

### 7.3 Wiring — protect everything except auth

Add a router-level dependency to **both existing routers** (this protects every current and future endpoint on those routers with one line each; no per-endpoint edits):

```python
# app/api/complaints.py
router = APIRouter(
    prefix="/api/complaints",
    tags=["complaints"],
    dependencies=[Depends(get_current_user)],   # NEW
)

# app/api/ai.py
router = APIRouter(
    prefix="/api/ai",
    tags=["ai agent"],
    dependencies=[Depends(get_current_user)],   # NEW
)
```

Open (unauthenticated) surface — keep exactly this:
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh` (auth bootstrap)
- `GET /` and `GET /health` (health checks / demo landing)

`app/main.py` additions:

```python
from app.api import ai_router, auth_router, complaints_router
...
app.include_router(auth_router)     # NEW — must be registered so /api/auth/* is reachable
```

### 7.4 Why router-level dependencies over a global middleware

- Keeps OpenAPI accurate: Swagger shows the lock icon + 401 on protected routes, and "Authorize" works.
- Errors are proper `HTTPException`s with `WWW-Authenticate`, not raw 500s from middleware plumbing.
- `/api/auth/*` and `/health` stay open without path-allowlist hacks.

### 7.5 Role enforcement

The `role` field is stored and returned, but **no endpoint enforces admin-only behavior yet** (out of scope for this round; all authenticated users can CRUD). Add `require_role("admin")` as a second dependency layered on `get_current_user` when admin-only actions exist (e.g., user management, complaint deletion). Note in README so it's not mistaken for RBAC.

---

## 8. Error Format & Consistency

The codebase convention (verified in `app/api/complaints.py`) is:

```python
raise HTTPException(status_code=404, detail="Complaint not found")
```

The auth spec keeps that exact shape:

| Status | Meaning | Body |
|---|---|---|
| 400 | (reserved, not currently used) | `{"detail": "..."}` |
| 401 | Auth failure | `{"detail": "..."}` + `WWW-Authenticate: Bearer` header |
| 404 | (used by complaints only today) | `{"detail": "..."}` |
| 409 | Conflict (duplicate email) | `{"detail": "Email already registered"}` |
| 422 | Validation failure | FastAPI default: `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` |

Frontend already reads `body.detail` in `api.js` — that logic stays. For 422, `detail` is an **array**, so the frontend error mapping should render `detail.map(d => d.msg).join(", ")` instead of stringifying the array (§12.4).

---

## 9. Alembic Migration

One new migration: **add `users` table**. No changes to existing tables.

### 9.1 Before generating — register the model for autogenerate

`backend/alembic/env.py` currently does:

```python
from app.models import Complaint, StatusHistory  # noqa: F401 - register models
```

Update to:

```python
from app.models import Complaint, StatusHistory, User  # noqa: F401 - register models
```

Without this, `--autogenerate` silently produces an empty migration.

### 9.2 Exact command sequence (Windows, from repo root)

```powershell
cd backend
.venv\Scripts\activate
pip install -r requirements.txt          # picks up new auth pins
alembic revision --autogenerate -m "add users table"
```

Then **review** the generated file in `alembic/versions/` — it must contain **only** the `users` table (autogenerate can also detect drift in existing tables; if it emits anything touching `complaints`/`status_history`, delete those lines). Expected body:

```python
def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
```

All types (`String`, `Boolean`, `DateTime`) are SQLite-compatible; **no Enum, no server_default, no native UUID** (matches the existing `complaints` migration exactly).

```powershell
alembic upgrade head
```

### 9.3 ⚠️ SQLite gotcha — the fallback is app-only, not alembic

`app/database.py` falls back to SQLite at **runtime**, but `alembic/env.py` uses `settings.database_url` verbatim. If Postgres is down, `alembic upgrade head` fails — it will not silently fall back.

- Postgres available → nothing to do; migrations run against Postgres.
- Local-only testing on SQLite → set in `backend/.env`:

  ```
  DATABASE_URL=sqlite:///./complaints.db
  ```

  then run `alembic upgrade head` against the same file the app uses. Migrations are forward-only in SQLite (no `ALTER` needed here since we're only `CREATE TABLE` — fine).

---

## 10. Security Checklist

| # | Item | Spec |
|---|---|---|
| 1 | Password minimum | **8 chars** (`min_length=8` in `UserCreate`). Max 72 chars (bcrypt byte limit — see §4.2). |
| 2 | Email normalization | `strip().lower()` in schema validator **and** CRUD. Uniqueness enforced by DB unique index (final backstop) + pre-check → 409. |
| 3 | Hashing algorithm | bcrypt, **cost factor 12** (passlib default; ~0.2–0.3 s/hash — fine for demo, note in docs). Never store plaintext. |
| 4 | No plaintext logging | **Never log passwords, tokens, or the JWT secret.** Existing `_redact()` in `database.py` is the pattern for URLs. On `register`/`login` success, log only `user.id` + email (email is PII — fine at INFO for demo, avoid in prod). |
| 5 | Login error ambiguity | Identical `"Incorrect email or password"` for unknown email vs wrong password (no user enumeration). |
| 6 | Rate limiting (optional for demo) | `/api/auth/login` + `/api/auth/register` are the only unauthenticated attack surfaces. Recommendation: a trivial in-memory limiter (e.g., per-IP, 10/min on login) or `slowapi`; mark as **future work** — not blocking the assessment demo. |
| 7 | CORS | Already configured in `main.py` (`CORSMiddleware`, `allow_credentials=True`, origins from `CORS_ORIGINS`). **Do not modify** — Bearer headers are not affected by the credentials flag. Re-verify after wiring auth that the middleware block is untouched. |
| 8 | Secret hygiene | `JWT_SECRET` from `.env` (never committed); fixed dev default, not random-per-boot (§5.1). Rotating it invalidates all tokens. |
| 9 | Token hygiene | `type` claim separates access/refresh; `sub` is the DB id (live user lookup on every request → deactivation is instant); 60-min access expiry. |
| 10 | Transport | All calls through the Vite proxy in dev; production must terminate TLS at the edge (deployment note only). |
| 11 | XSS / token storage | Frontend stores tokens in **localStorage → XSS-exfiltratable**; §12.1 gives the storage guidance + warning. |

---

## 11. Demo Bootstrap & Docs to Update

### 11.1 Seed an admin for the demo

After `alembic upgrade head`, promote one account (or use the login of any registered user for the analyst flow):

```sql
-- PostgreSQL
UPDATE users SET role='admin' WHERE email='demo.admin@pharmacare.dev';

-- SQLite (same SQL works)
UPDATE users SET role='admin' WHERE email='demo.admin@pharmacare.dev';
```

Optional (nice for the demo script): extend `app/seed.py` to create `demo.admin@pharmacare.dev` + one analyst user if the `users` table is empty.

### 11.2 Docs to update (small, explicit)

- `README.md`: remove the `no user auth (single-tenant demo scope)` stub; add an **Authentication** section (register/login/me/refresh), the new env vars table rows (`JWT_SECRET` etc.), and the two new API rows (`POST /api/auth/login`, `POST /api/auth/me`, etc.).
- `docs/DEMO_SCRIPT.md`: add a 30-second auth segment (register → Swagger Authorize → protected calls) since both demo videos now must authenticate.

---

## 12. Frontend Integration Contract (for the designer)

Contract only — UI design is handled separately. Required behavior:

### 12.1 Token storage (decide once)

- **Recommended for this demo:** `access_token` in **Redux memory only**; `refresh_token` in **localStorage** (key `pharmacare_refresh_token`) so the session survives F5 mid-demo.
- ⚠️ **Warning to surface in code review:** localStorage is readable by any injected script (XSS). Acceptable for the assessment demo; production path is HttpOnly cookies or memory-only + forced re-login on reload.
- On app boot: if a refresh token exists → call `/api/auth/refresh` → restore session silently; else → `/login`.

### 12.2 API client changes (`frontend/src/services/api.js`)

1. Add `auth` state holder (module-level `let accessToken = null; export const setAccessToken = (t) => ...` or read from the Redux store — designer's choice; keep `api.js` free of React context).
2. **Inject header on every request** to protected routes:

   ```
   Authorization: Bearer <access_token>
   ```

   All existing calls (`listComplaints`, `aiAssess`, …) are to protected routes once §7.3 lands — one interceptor covers everything.
3. **401 handling:** on any 401 that is *not* from `/api/auth/login` or `/api/auth/refresh`: call `POST /api/auth/refresh` once with the stored refresh token → on success retry the original request once; on failure → clear auth state, redirect to `/login`.
4. Keep the existing error mapping (`body.detail`), add the 422 array handling (§8).

### 12.3 New auth endpoints in the client

| Method/Path | Body | Notes |
|---|---|---|
| `POST /api/auth/register` | JSON `{full_name, email, password}` | 201 → redirect to `/login` |
| `POST /api/auth/login` | **`application/x-www-form-urlencoded`**: `username=<email>&password=<pw>` | ⚠️ **Not JSON.** Use `URLSearchParams` as fetch body + set `Content-Type: application/x-www-form-urlencoded`. Store both tokens on success. |
| `GET /api/auth/me` | — | Fetch user profile after login/refresh; seed Redux `auth` slice |
| `POST /api/auth/refresh` | JSON `{refresh_token}` | Proactive refresh: schedule ~55 min after login, and on boot, and on 401 |

### 12.4 Redux shape (suggestion)

```js
auth: { user: UserOut|null, accessToken: string|null, status: 'idle'|'loading'|'authenticated'|'unauthenticated', error: string|null }
```

- New `authSlice.js` registered in `store/index.js` (next to `complaints`/`ai`).
- Route guard: redirect unauthenticated users to `/login`; redirect authenticated users away from `/login`.

---

## 13. Implementation Checklist (file-by-file)

| # | File | Change |
|---|---|---|
| 1 | `backend/requirements.txt` | Add `passlib==1.7.4`, `bcrypt==4.0.1`, `PyJWT==2.10.1`, `email-validator==2.2.0` |
| 2 | `backend/app/models/user.py` | **New** — `User` model + `UserRole` enum (§4.1) |
| 3 | `backend/app/models/__init__.py` | Export `User`, `UserRole` |
| 4 | `backend/app/schemas/auth.py` | **New** — `UserCreate`, `UserOut`, `Token`, `RefreshRequest` (§4.2) |
| 5 | `backend/app/schemas/__init__.py` | Export new schemas |
| 6 | `backend/app/crud/user.py` | **New** — `get_user_by_email`, `get_user_by_id`, `create_user` (normalize email; unique check → caller raises 409) |
| 7 | `backend/app/security.py` | **New** — hashing + JWT helpers (§7.1) |
| 8 | `backend/app/api/deps.py` | **New** — `oauth2_scheme`, `get_current_user` (§7.2) |
| 9 | `backend/app/api/auth.py` | **New** — register / login / me / refresh router (§6) |
| 10 | `backend/app/api/__init__.py` | Export `auth_router` |
| 11 | `backend/app/api/complaints.py` | Add `dependencies=[Depends(get_current_user)]` to router |
| 12 | `backend/app/api/ai.py` | Same as #11 |
| 13 | `backend/app/main.py` | Include `auth_router`; leave CORS + health untouched |
| 14 | `backend/app/config.py` | Add 4 JWT settings (§5.1) |
| 15 | `backend/.env.example` | Add JWT block (§5.2) |
| 16 | `backend/alembic/env.py` | Import `User` |
| 17 | `alembic/versions/<rev>_add_users_table.py` | **New** — generated + reviewed (§9) |
| 18 | `README.md`, `docs/DEMO_SCRIPT.md` | Update per §11.2 |
| 19 | `frontend/src/services/api.js` + new `authSlice` | Per §12 (designer) |

**Manual test pass (post-implementation):**
1. `POST /api/auth/register` → 201; duplicate email → 409.
2. `POST /api/auth/login` (form-encoded!) → tokens; wrong password → 401.
3. `GET /api/auth/me` with token → user; without → 401.
4. `GET /api/complaints` without token → 401; with token → 200.
5. `POST /api/auth/refresh` → new access token; expired/garbage refresh → 401.
6. Swagger: click **Authorize**, paste username(email)/password → protected routes turn callable.
7. Run once against **Postgres** and once against **SQLite** (`DATABASE_URL=sqlite:///./complaints.db`) — both must pass steps 1–6 identically.

---

## 14. Lead-Dev Warning List (copy-paste into the ticket)

1. **`bcrypt` must stay `<4.1`** — `passlib 1.7.4` crashes with `AttributeError: module 'bcrypt' has no attribute '__about__'` on bcrypt ≥ 4.1 (or 5.x). Pin `bcrypt==4.0.1` in `requirements.txt`; verify with the one-liner in §3.1 after install.
2. **Login is form-encoded, not JSON** — `OAuth2PasswordRequestForm` requires `username`/`password` as `application/x-www-form-urlencoded`. The frontend MUST NOT send a JSON body to `/api/auth/login`, or they'll get a 422. `python-multipart` is already pinned — don't re-add.
3. **`alembic upgrade head` does NOT inherit the SQLite fallback** — `database.py` falls back at runtime only; `alembic/env.py` uses `DATABASE_URL` as-is. For SQLite-only runs, set `DATABASE_URL=sqlite:///./complaints.db` in `.env` first (§9.3).
4. **Register `User` in `alembic/env.py` before `--autogenerate`**, or the migration comes out empty (§9.1). Review the generated migration — discard any drift on `complaints`/`status_history`.
5. **No `Enum` column type in the `users` table** — SQLite has no native ENUMs. `role` is `String(20)` with the `UserRole` enum used only in code (same pattern as `complaints.status`).
6. **`sub` must be a string** — our UUID-string ids are already correct; don't "helpfully" cast to int.
7. **Fixed dev `JWT_SECRET` default, never random-per-boot** — a per-boot random secret logs everyone out on every restart; a *rotating* secret invalidates all tokens (planned rotation only).
8. **`email-validator` is a new dependency** — `EmailStr` in Pydantic 2 fails at import time without it.
9. **Don't touch `main.py` CORS block** — auth headers work through the existing middleware unchanged.
10. **`password` max_length=72** is intentional (bcrypt truncation) — do not "fix" it to 128.

---

## 15. Out of Scope / Future Work

- Refresh-token rotation / revocation (denylist table or `token_version` column on `users`).
- RBAC enforcement (`require_role("admin")` on user-management and destructive endpoints).
- Password reset / change flows, email verification, MFA.
- Server-side rate limiting on `/api/auth/*` (simple in-memory limiter or `slowapi`).
- HttpOnly-cookie session option for production hardening.
