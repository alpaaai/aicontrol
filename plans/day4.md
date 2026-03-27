# AIControl Day 4 — Policy CRUD + JWT Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** JWT authentication on `/intercept` and `/policies` endpoints, plus full policy CRUD API. Two roles: `agent` (intercept only) and `admin` (policies + intercept). Non-expiring tokens, revoked by deleting from DB. A `scripts/issue_token.py` CLI issues tokens for customers.

**Architecture:** Tokens are signed JWTs (HS256) using `SECRET_KEY` from `.env`. Token metadata (role, description, revoked flag) stored in a new `api_tokens` table. Every protected request validates the JWT signature then checks the DB that it hasn't been revoked. FastAPI dependency injection handles auth — routes don't change, just add `Depends(require_agent)` or `Depends(require_admin)`.

**Tech Stack:** python-jose (JWT), passlib, FastAPI Depends, SQLAlchemy async, Alembic

---

## File Map

| File | Purpose |
|---|---|
| `app/models/schemas.py` | Add `APIToken` ORM model |
| `migrations/versions/<hash>_add_api_tokens.py` | Migration adding api_tokens table |
| `app/core/auth.py` | JWT sign/verify, FastAPI auth dependencies (`require_agent`, `require_admin`) |
| `app/routers/intercept.py` | Add `require_agent` dependency |
| `app/routers/policies.py` | New router — full CRUD, protected by `require_admin` |
| `app/main.py` | Mount policies router |
| `scripts/issue_token.py` | CLI to issue tokens: `python scripts/issue_token.py --role admin --desc "Customer A"` |
| `scripts/revoke_token.py` | CLI to revoke tokens by ID |
| `tests/test_auth.py` | Tests for JWT sign/verify and auth dependencies |
| `tests/test_policies_api.py` | Tests for policy CRUD endpoints |

---

## Task 1: APIToken Model + Migration

`APIToken` ORM model stores token metadata. The JWT itself is stateless but we check this table on every request to support revocation.

**Files:**
- Modify: `app/models/schemas.py`
- Create: migration via alembic

- [ ] **Step 1: Write the failing test**

```bash
cat > ~/aicontrol/tests/test_api_token_model.py << 'EOF'
"""Tests for APIToken ORM model."""
from sqlalchemy import inspect as sa_inspect


def _cols(model):
    return {c.key: c for c in sa_inspect(model).columns}


def test_api_token_table_name():
    from app.models.schemas import APIToken
    assert APIToken.__tablename__ == "api_tokens"


def test_api_token_required_columns():
    from app.models.schemas import APIToken
    cols = _cols(APIToken)
    for name in ["id", "token_hash", "role", "description", "revoked", "created_at"]:
        assert name in cols, f"api_tokens missing column: {name}"


def test_api_token_role_values():
    """Role column must exist and be a string type."""
    from app.models.schemas import APIToken
    from sqlalchemy import String
    cols = _cols(APIToken)
    assert isinstance(cols["role"].columns[0].type, String)
EOF
```

- [ ] **Step 2: Run test — verify it FAILS**

```bash
cd ~/aicontrol && pytest tests/test_api_token_model.py -v
```
Expected: `ImportError` — `APIToken` not in schemas yet.

- [ ] **Step 3: Add `APIToken` to `app/models/schemas.py`**

Append to the end of `app/models/schemas.py`:

```python
class APIToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )
```

- [ ] **Step 4: Run test — verify it PASSES**

```bash
cd ~/aicontrol && pytest tests/test_api_token_model.py -v
```
Expected: `3 passed`.

- [ ] **Step 5: Generate and apply migration**

```bash
cd ~/aicontrol
alembic revision --autogenerate -m "add_api_tokens"
alembic upgrade head
```

Verify:
```bash
docker compose exec postgres psql -U aicontrol -d aicontrol -c "\d api_tokens"
```
Expected: table with `id`, `token_hash`, `role`, `description`, `revoked`, `created_at`.

- [ ] **Step 6: Commit**

```bash
cd ~/aicontrol
git add app/models/schemas.py migrations/ tests/test_api_token_model.py
git commit -m "feat: add api_tokens model and migration"
```

---

## Task 2: JWT Auth Core

`app/core/auth.py` — signs and verifies JWTs, checks revocation in DB, exposes two FastAPI dependencies: `require_agent` and `require_admin`.

**Files:**
- Create: `app/core/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Install python-jose**

```bash
pip install python-jose[cryptography] --break-system-packages
```

- [ ] **Step 2: Write the failing tests**

```bash
cat > ~/aicontrol/tests/test_auth.py << 'EOF'
"""Tests for JWT sign/verify logic."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def test_create_token_returns_string():
    """create_token must return a non-empty string."""
    from app.core.auth import create_token
    token = create_token(role="agent", description="test")
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_token_different_each_time():
    """Two tokens with same role must be different (unique jti)."""
    from app.core.auth import create_token
    t1 = create_token(role="agent", description="a")
    t2 = create_token(role="agent", description="b")
    assert t1 != t2


def test_decode_token_returns_payload():
    """decode_token must return payload with role and jti."""
    from app.core.auth import create_token, decode_token
    token = create_token(role="admin", description="test")
    payload = decode_token(token)
    assert payload["role"] == "admin"
    assert "jti" in payload


def test_decode_token_invalid_raises():
    """decode_token must raise on invalid token."""
    from app.core.auth import decode_token
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_hash_token_is_deterministic():
    """Same token string must always produce same hash."""
    from app.core.auth import hash_token
    assert hash_token("abc") == hash_token("abc")


def test_hash_token_different_inputs():
    """Different tokens must produce different hashes."""
    from app.core.auth import hash_token
    assert hash_token("abc") != hash_token("def")
EOF
```

- [ ] **Step 3: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_auth.py -v
```
Expected: `ImportError` for `app.core.auth`.

- [ ] **Step 4: Write `app/core/auth.py`**

```bash
cat > ~/aicontrol/app/core/auth.py << 'EOF'
"""JWT authentication — sign, verify, revocation check, FastAPI dependencies."""
import hashlib
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import get_db
from app.models.schemas import APIToken

ALGORITHM = "HS256"
bearer_scheme = HTTPBearer()


def hash_token(token: str) -> str:
    """SHA-256 hash of a token string for DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(role: str, description: str) -> str:
    """Issue a new non-expiring JWT with a unique jti."""
    payload = {
        "jti": str(uuid.uuid4()),
        "role": role,
        "description": description,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify JWT signature. Raises JWTError if invalid."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


async def _get_verified_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify JWT signature and check revocation. Returns payload."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
        )

    token_hash = hash_token(token)
    result = await db.execute(
        select(APIToken).where(
            APIToken.token_hash == token_hash,
            APIToken.revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found or revoked",
        )
    return payload


async def require_agent(payload: dict = Depends(_get_verified_token)) -> dict:
    """Dependency: requires agent or admin role."""
    if payload.get("role") not in ("agent", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent or admin role required",
        )
    return payload


async def require_admin(payload: dict = Depends(_get_verified_token)) -> dict:
    """Dependency: requires admin role only."""
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return payload
EOF
```

- [ ] **Step 5: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_auth.py -v
```
Expected: `6 passed`.

- [ ] **Step 6: Commit**

```bash
cd ~/aicontrol
git add app/core/auth.py tests/test_auth.py
git commit -m "feat: add jwt auth core with sign verify and fastapi dependencies"
```

---

## Task 3: Token Issuance + Revocation Scripts

`scripts/issue_token.py` — CLI that creates a JWT, stores its hash in `api_tokens`, and prints the token once. `scripts/revoke_token.py` — marks a token revoked by ID.

**Files:**
- Create: `scripts/issue_token.py`
- Create: `scripts/revoke_token.py`

- [ ] **Step 1: Write `scripts/issue_token.py`**

```bash
cat > ~/aicontrol/scripts/issue_token.py << 'EOF'
"""Issue a new API token and store its hash in the DB.

Usage:
    python scripts/issue_token.py --role agent --desc "Insurance claims agent"
    python scripts/issue_token.py --role admin --desc "Customer A admin"
"""
import argparse
import asyncio

from sqlalchemy import text
from app.core.auth import create_token, hash_token
from app.models.database import async_session_factory


async def issue(role: str, description: str) -> None:
    if role not in ("agent", "admin"):
        print(f"Error: role must be 'agent' or 'admin', got '{role}'")
        return

    token = create_token(role=role, description=description)
    token_hash = hash_token(token)

    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                INSERT INTO api_tokens (token_hash, role, description, revoked)
                VALUES (:hash, :role, :desc, false)
                RETURNING id
            """),
            {"hash": token_hash, "role": role, "desc": description},
        )
        token_id = result.scalar_one()
        await session.commit()

    print(f"\nToken issued successfully")
    print(f"ID:          {token_id}")
    print(f"Role:        {role}")
    print(f"Description: {description}")
    print(f"\nToken (store securely — shown once only):")
    print(f"\n  {token}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Issue an AIControl API token")
    parser.add_argument("--role", required=True, choices=["agent", "admin"])
    parser.add_argument("--desc", required=True, help="Description for this token")
    args = parser.parse_args()
    asyncio.run(issue(args.role, args.desc))
EOF
```

- [ ] **Step 2: Write `scripts/revoke_token.py`**

```bash
cat > ~/aicontrol/scripts/revoke_token.py << 'EOF'
"""Revoke an API token by its DB ID.

Usage:
    python scripts/revoke_token.py --id <uuid>
"""
import argparse
import asyncio

from sqlalchemy import text
from app.models.database import async_session_factory


async def revoke(token_id: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                UPDATE api_tokens SET revoked = true
                WHERE id = :id AND revoked = false
                RETURNING id, description, role
            """),
            {"id": token_id},
        )
        row = result.mappings().one_or_none()
        await session.commit()

    if row is None:
        print(f"No active token found with ID: {token_id}")
    else:
        print(f"Revoked token: {row['description']} (role={row['role']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Revoke an AIControl API token")
    parser.add_argument("--id", required=True, help="Token UUID to revoke")
    args = parser.parse_args()
    asyncio.run(revoke(args.id))
EOF
```

- [ ] **Step 3: Smoke test — issue a token (local dev)**

```bash
cd ~/aicontrol && python scripts/issue_token.py --role agent --desc "Test agent token"
```
Expected: Token printed to stdout with ID and role.

- [ ] **Step 4: Smoke test — issue admin token (local dev)**

```bash
cd ~/aicontrol && python scripts/issue_token.py --role admin --desc "Test admin token"
```
Save both tokens — you'll need them for endpoint tests.

> **Customer-facing method (document this in onboarding guide):**
> Customers run scripts via `docker compose exec` — no Python install needed on host:
> ```bash
> # Issue agent token
> docker compose exec api python scripts/issue_token.py \
>   --role agent --desc "Claims processing agent"
>
> # Issue admin token
> docker compose exec api python scripts/issue_token.py \
>   --role admin --desc "IT admin"
>
> # Revoke a token by ID
> docker compose exec api python scripts/revoke_token.py \
>   --id <token-uuid>
> ```
> Tokens are shown once — customer must store them securely (password manager, secrets vault).

- [ ] **Step 5: Commit**

```bash
cd ~/aicontrol
git add scripts/issue_token.py scripts/revoke_token.py
git commit -m "feat: add token issuance and revocation scripts"
```

---

## Task 4: Protect /intercept with require_agent

Add `require_agent` dependency to the intercept endpoint. Existing tests need updating to pass a valid token.

**Files:**
- Modify: `app/routers/intercept.py`
- Modify: `tests/test_intercept.py`

- [ ] **Step 1: Write the failing test**

```bash
cat >> ~/aicontrol/tests/test_intercept.py << 'EOF'


@pytest.mark.asyncio
async def test_intercept_requires_auth():
    """POST /intercept without token must return 403."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/intercept", json=make_payload())
    assert response.status_code in (401, 403)
EOF
```

- [ ] **Step 2: Run test — verify it FAILS**

```bash
cd ~/aicontrol && pytest tests/test_intercept.py::test_intercept_requires_auth -v
```
Expected: `FAILED` — currently returns 200 (no auth yet).

- [ ] **Step 3: Add `require_agent` to intercept router**

In `app/routers/intercept.py`, update the import and endpoint signature:

```python
# Add to imports
from app.core.auth import require_agent

# Update endpoint signature
@router.post("/intercept", response_model=InterceptResponse)
async def intercept(
    request: InterceptRequest,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_agent),
) -> InterceptResponse:
```

- [ ] **Step 4: Update existing intercept tests to mock auth**

In `tests/test_intercept.py`, add auth mock to all existing passing tests. Add this helper at the top of the test file:

```python
from unittest.mock import patch

def _mock_auth():
    """Context manager that bypasses JWT auth for tests."""
    return patch(
        "app.routers.intercept.require_agent",
        return_value={"role": "agent"}
    )
```

Wrap each existing test's `with patch(...)` block to also include `_mock_auth()`:

```python
@pytest.mark.asyncio
async def test_intercept_returns_200():
    from app.main import app
    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "allow", "reason": "default_allow"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=uuid.uuid4()
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )), patch("app.core.auth._get_verified_token", new=AsyncMock(
        return_value={"role": "agent"}
    )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())
    assert response.status_code == 200
```

Apply same `_get_verified_token` mock patch to all other intercept tests.

- [ ] **Step 5: Run all intercept tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_intercept.py -v
```
Expected: All pass including `test_intercept_requires_auth`.

- [ ] **Step 6: Commit**

```bash
cd ~/aicontrol
git add app/routers/intercept.py tests/test_intercept.py
git commit -m "feat: protect /intercept with require_agent jwt auth"
```

---

## Task 5: Policy CRUD Router

`app/routers/policies.py` — full CRUD for policies, protected by `require_admin`. Also triggers OPA reload on create/update/delete so the running system picks up changes immediately.

**Files:**
- Create: `app/routers/policies.py`
- Create: `tests/test_policies_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests**

```bash
cat > ~/aicontrol/tests/test_policies_api.py << 'EOF'
"""Tests for policy CRUD endpoints."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


def _auth_patch():
    return patch(
        "app.core.auth._get_verified_token",
        new=AsyncMock(return_value={"role": "admin"})
    )


def _opa_patch():
    return patch(
        "app.services.policy_loader.push_rego_to_opa",
        new=AsyncMock(return_value=None)
    )


@pytest.mark.asyncio
async def test_list_policies_returns_200():
    from app.main import app
    with _auth_patch(), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/policies")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_policies_returns_list():
    from app.main import app
    with _auth_patch(), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/policies")
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_policy_returns_201():
    from app.main import app
    payload = {
        "name": f"test_policy_{uuid.uuid4().hex[:6]}",
        "rule_type": "tool_blacklist",
        "condition": {"blocked_tools": ["bad_tool"]},
        "action": "deny",
        "severity": "high",
        "description": "Test policy",
        "compliance_frameworks": [],
    }
    with _auth_patch(), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/policies", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_policy_requires_admin():
    from app.main import app
    with patch(
        "app.core.auth._get_verified_token",
        new=AsyncMock(return_value={"role": "agent"})
    ), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/policies", json={
                "name": "test", "rule_type": "default_allow",
                "condition": {}, "action": "allow",
                "severity": "low", "compliance_frameworks": [],
            })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_policy_returns_404_for_missing():
    from app.main import app
    with _auth_patch(), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/policies/{uuid.uuid4()}")
    assert response.status_code == 404
EOF
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_policies_api.py -v
```
Expected: `ImportError` or 404 — router not mounted yet.

- [ ] **Step 3: Write `app/routers/policies.py`**

```bash
cat > ~/aicontrol/app/routers/policies.py << 'EOF'
"""Policy CRUD endpoints — admin only."""
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.models.database import get_db
from app.models.schemas import Policy
from app.services.policy_loader import push_rego_to_opa

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    condition: dict[str, Any]
    action: str
    severity: str = "medium"
    compliance_frameworks: list[str] = []


class PolicyUpdate(BaseModel):
    description: Optional[str] = None
    condition: Optional[dict[str, Any]] = None
    action: Optional[str] = None
    severity: Optional[str] = None
    active: Optional[bool] = None
    compliance_frameworks: Optional[list[str]] = None


class PolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    rule_type: str
    condition: dict[str, Any]
    action: str
    severity: Optional[str]
    active: Optional[bool]
    compliance_frameworks: Optional[list]

    class Config:
        from_attributes = True


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> list[PolicyResponse]:
    result = await db.execute(select(Policy).order_by(Policy.name))
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> PolicyResponse:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> PolicyResponse:
    policy = Policy(
        name=body.name,
        description=body.description,
        rule_type=body.rule_type,
        condition=body.condition,
        action=body.action,
        severity=body.severity,
        compliance_frameworks=body.compliance_frameworks,
        active=True,
    )
    db.add(policy)
    await db.flush()
    await push_rego_to_opa()
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    body: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> PolicyResponse:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(policy, field, value)
    await db.flush()
    await push_rego_to_opa()
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> None:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(policy)
    await push_rego_to_opa()
EOF
```

- [ ] **Step 4: Mount policies router in `app/main.py`**

Add to `app/main.py`:
```python
from app.routers.policies import router as policies_router
app.include_router(policies_router)
```

- [ ] **Step 5: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_policies_api.py -v
```
Expected: `5 passed`.

- [ ] **Step 6: Commit**

```bash
cd ~/aicontrol
git add app/routers/policies.py tests/test_policies_api.py app/main.py
git commit -m "feat: add policy crud router protected by admin jwt"
```

---

## Task 6: Full Verification

- [x] **Step 1: Run full test suite**

```bash
cd ~/aicontrol && pytest tests/ -v
```
Expected: All tests pass.

- [x] **Step 2: Start server**

```bash
cd ~/aicontrol && uvicorn app.main:app --reload --port 8000
```

- [x] **Step 3: Issue tokens**

```bash
# Local dev
python scripts/issue_token.py --role agent --desc "Demo agent"
python scripts/issue_token.py --role admin --desc "Demo admin"
# Save both as AGENT_TOKEN and ADMIN_TOKEN

# Customer-facing equivalent
docker compose exec api python scripts/issue_token.py --role agent --desc "Demo agent"
docker compose exec api python scripts/issue_token.py --role admin --desc "Demo admin"
```

- [x] **Step 4: Verify /intercept requires auth**

```bash
# No token — expect 403
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -d '{"session_id":"00000000-0000-0000-0000-000000000002","agent_id":"00000000-0000-0000-0000-000000000001","agent_name":"demo-agent","tool_name":"safe_tool","tool_parameters":{},"sequence_number":1}'

# With agent token — expect allow decision
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -d '{"session_id":"00000000-0000-0000-0000-000000000002","agent_id":"00000000-0000-0000-0000-000000000001","agent_name":"demo-agent","tool_name":"safe_tool","tool_parameters":{},"sequence_number":1}'
```

- [x] **Step 5: Verify /policies requires admin**

```bash
# Agent token on admin endpoint — expect 403
curl -s http://localhost:8000/policies \
  -H "Authorization: Bearer $AGENT_TOKEN"

# Admin token — expect list of policies
curl -s http://localhost:8000/policies \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
```

- [x] **Step 6: Create a policy via API**

```bash
curl -s -X POST http://localhost:8000/policies \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "block_test_tool",
    "rule_type": "tool_blacklist",
    "condition": {"blocked_tools": ["test_bad_tool"]},
    "action": "deny",
    "severity": "high",
    "compliance_frameworks": ["SOC2"]
  }' | python3 -m json.tool
```
Expected: `201` with policy JSON including `id`.

- [x] **Step 7: Revoke a token**

```bash
python scripts/revoke_token.py --id <token-id-from-step-3>

# Verify revoked token is rejected
curl -s -X POST http://localhost:8000/intercept \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"00000000-0000-0000-0000-000000000002","agent_id":"00000000-0000-0000-0000-000000000001","agent_name":"demo-agent","tool_name":"safe_tool","tool_parameters":{},"sequence_number":1}'
```
Expected: `401 Token not found or revoked`.

- [x] **Step 8: Final commit**

```bash
cd ~/aicontrol
git add -A
git commit -m "chore: day 4 complete — jwt auth and policy crud verified"
```

---

## Troubleshooting Quick Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: jose` | Not installed | `pip install python-jose[cryptography] --break-system-packages` |
| `401 Token not found` | Token not in DB | Run `issue_token.py` first |
| `403 Admin role required` | Using agent token on admin endpoint | Use admin token |
| OPA push fails on policy create | OPA not running | `docker compose up -d` |
| Migration fails | `api_tokens` already exists | `alembic downgrade -1` then `upgrade head` |
| Tests fail after auth added | Missing `_get_verified_token` mock | Add mock patch to affected tests |
