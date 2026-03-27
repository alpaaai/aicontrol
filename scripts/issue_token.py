"""Issue a new API token and store its hash in the DB.

Usage:
    python scripts/issue_token.py --role agent --desc "Insurance claims agent"
    python scripts/issue_token.py --role admin --desc "Customer A admin"
"""
import argparse
import asyncio
import os

# Prevent SQLAlchemy echo logging — engine checks APP_ENV at import time
os.environ.setdefault("APP_ENV", "production")

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
                INSERT INTO api_tokens (id, token_hash, role, description, revoked)
                VALUES (gen_random_uuid(), :hash, :role, :desc, false)
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
