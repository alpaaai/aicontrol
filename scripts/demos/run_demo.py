#!/usr/bin/env python3
"""
AIControl Demo Runner — select scenario by name
Usage: python scripts/demos/run_demo.py --scenario lending --token $TOKEN --mode walkthrough
"""

import argparse
import importlib
import asyncio
import os
import sys

# Ensure repo root is on sys.path so `scripts.demos.*` imports resolve
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

SCENARIOS = {
    "lending":       "scripts.demos.demo_lending",
    "manufacturing": "scripts.demos.demo_manufacturing",
    "healthcare":    "scripts.demos.demo_healthcare",
    "support":       "scripts.demos.demo_support",
    "itsm":          "scripts.demos.demo_itsm",
    "revops":        "scripts.demos.demo_revops",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="AIControl Demo Runner")
    parser.add_argument("--scenario", required=True, choices=list(SCENARIOS.keys()),
                        help=f"Scenario to run: {', '.join(SCENARIOS.keys())}")
    parser.add_argument("--token", required=True, help="Agent JWT token")
    parser.add_argument("--mode", choices=["fast", "walkthrough"], default="walkthrough",
                        help="fast = no pauses, walkthrough = press ENTER between calls")
    args = parser.parse_args()

    module = importlib.import_module(SCENARIOS[args.scenario])
    asyncio.run(module.run_demo(args.token, args.mode))


if __name__ == "__main__":
    main()
