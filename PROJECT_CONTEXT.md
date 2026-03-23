# AIControl — Project Context

## What We Are Building
Enterprise AI agent governance infrastructure. Sits in agent execution loops.
Intercepts tool calls before they execute. Enforces policy. Logs everything.

## Stack
- Python 3.14
- FastAPI (API and proxy layer)
- SQLAlchemy + Alembic (ORM and migrations)
- PostgreSQL (audit store)
- OPA - Open Policy Agent (policy evaluation)
- Streamlit (dashboard)
- Slack Bolt (human review notifications)
- Docker Compose (local and customer deployment)

## OS
Ubuntu WSL2 on Windows

## Project Structure
~/dev/aicontrol/

## Current Phase
V1 prototype — Week 1, Day 1
