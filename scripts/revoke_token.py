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
