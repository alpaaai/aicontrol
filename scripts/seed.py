"""Insert demo agent and session for manual testing."""
import asyncio
import uuid
from sqlalchemy import text
from app.models.database import async_session_factory

AGENT_ID = "00000000-0000-0000-0000-000000000001"
SESSION_ID = "00000000-0000-0000-0000-000000000002"


async def seed():
    async with async_session_factory() as session:
        await session.execute(text("""
            INSERT INTO agents (id, name, owner, status, approved_tools)
            VALUES (:id, :name, :owner, :status, CAST(:tools AS jsonb))
            ON CONFLICT (id) DO NOTHING
        """), {"id": AGENT_ID, "name": "demo-agent",
               "owner": "demo@aicontrol.dev", "status": "approved",
               "tools": '["safe_tool", "http_request"]'})

        await session.execute(text("""
            INSERT INTO sessions (id, agent_id, status)
            VALUES (:id, :agent_id, :status)
            ON CONFLICT (id) DO NOTHING
        """), {"id": SESSION_ID, "agent_id": AGENT_ID, "status": "active"})

        await session.commit()
        print(f"Seeded agent_id={AGENT_ID}")
        print(f"Seeded session_id={SESSION_ID}")


asyncio.run(seed())
