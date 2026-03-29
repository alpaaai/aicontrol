"""Reset demo data for a clean demo run.

Usage:
    python scripts/demo_reset.py
"""
import asyncio
from sqlalchemy import text
from app.models.database import async_session_factory

AGENT_ID = "00000000-0000-0000-0000-000000000001"
SESSION_ID = "00000000-0000-0000-0000-000000000002"


async def reset():
    async with async_session_factory() as session:
        # Clear in FK-safe order
        await session.execute(text("DELETE FROM hitl_reviews"))
        await session.execute(text("DELETE FROM audit_events"))
        await session.execute(text("DELETE FROM sessions"))
        await session.execute(
            text("DELETE FROM agents WHERE id = :id"),
            {"id": AGENT_ID}
        )

        # Re-seed demo agent
        await session.execute(text("""
            INSERT INTO agents
                (id, name, owner, status, approved_tools)
            VALUES
                (:id, :name, :owner, :status, CAST(:tools AS jsonb))
            ON CONFLICT (id) DO UPDATE SET
                status = 'approved',
                name = EXCLUDED.name
        """), {
            "id": AGENT_ID,
            "name": "claims-processing-agent",
            "owner": "ai-team@acme-insurance.com",
            "status": "approved",
            "tools": '["lookup_policy", "calculate_payout", '
                     '"send_notification", "http_request", "flag_for_review"]',
        })

        await session.commit()

    print("Demo data reset complete.")
    print(f"Agent ID:   {AGENT_ID}")
    print(f"Session ID: {SESSION_ID} (created fresh on each demo run)")


asyncio.run(reset())
