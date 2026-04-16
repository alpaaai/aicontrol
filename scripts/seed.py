"""Insert demo agents and sessions for manual testing and demo scenarios."""
import asyncio
from sqlalchemy import text
from app.models.database import async_session_factory

AGENTS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "claims-processing-agent",
        "owner": "ai-team@acme-insurance.com",
        "status": "approved",
        "tools": '["process_claim", "query_policy", "approve_payment", "flag_fraud"]',
    },
    {
        "id": "00000000-0000-0000-0000-000000000010",
        "name": "loan-underwriting-agent",
        "owner": "lending-team@bank.com",
        "status": "approved",
        "tools": '["read_loan_application", "query_credit_bureau", "run_risk_model", "approve_loan"]',
    },
    {
        "id": "00000000-0000-0000-0000-000000000020",
        "name": "clinical-documentation-agent",
        "owner": "clinical-ops@hospital.org",
        "status": "approved",
        "tools": '["read_patient_record", "query_lab_results", "draft_clinical_note", "update_encounter"]',
    },
    {
        "id": "00000000-0000-0000-0000-000000000030",
        "name": "incident-response-agent",
        "owner": "platform-ops@company.com",
        "status": "approved",
        "tools": '["query_logs", "restart_service", "apply_config_patch", "escalate_incident", "execute_runbook"]',
    },
    {
        "id": "00000000-0000-0000-0000-000000000040",
        "name": "supplier-sourcing-agent",
        "owner": "procurement@manufacturer.com",
        "status": "approved",
        "tools": '["query_inventory", "search_supplier_catalog", "create_purchase_order", "http_post"]',
    },
    {
        "id": "00000000-0000-0000-0000-000000000050",
        "name": "support-resolution-agent",
        "owner": "cx-platform@company.com",
        "status": "approved",
        "tools": '["read_customer_account", "apply_service_credit", "resolve_ticket", "query_all_customers"]',
    },
    {
        "id": "00000000-0000-0000-0000-000000000060",
        "name": "crm-automation-agent",
        "owner": "revops@company.com",
        "status": "approved",
        "tools": '["update_deal_stage", "log_sales_activity", "enrich_contact", "query_all_accounts"]',
    },
]


async def seed():
    async with async_session_factory() as session:
        for agent in AGENTS:
            await session.execute(text("""
                INSERT INTO agents (id, name, owner, status, approved_tools)
                VALUES (:id, :name, :owner, :status, CAST(:tools AS jsonb))
                ON CONFLICT (id) DO NOTHING
            """), agent)
            print(f"Seeded agent: {agent['name']}  ({agent['id']})")

        await session.commit()
        print(f"\nDone — {len(AGENTS)} agents seeded.")


asyncio.run(seed())
