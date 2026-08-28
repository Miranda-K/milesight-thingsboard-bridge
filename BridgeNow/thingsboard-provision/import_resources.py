"""
Imports version-controlled rule chains and dashboards into ThingsBoard
via its REST API, so a fresh install doesn't require manually
re-uploading JSON through the UI.

Looks for:
  /import/rule_chains/*.json   -> exported rule chains (ruleChain + metadata)
  /import/dashboards/*.json    -> exported dashboards

Existing resources with a matching name/title are updated in place,
so this script is safe to re-run (e.g. after pulling repo updates).
"""

import glob
import json
import os
import sys
import time

import requests

TB_HOST = os.environ.get("TB_HOST", "http://thingsboard-ce:8080")
TB_ADMIN_EMAIL = os.environ.get("TB_ADMIN_EMAIL", "tenant@thingsboard.org")
TB_ADMIN_PASSWORD = os.environ.get("TB_ADMIN_PASSWORD", "tenant")

RULE_CHAINS_DIR = "/import/rule_chains"
DASHBOARDS_DIR = "/import/dashboards"

MAX_WAIT_SECONDS = 120
RETRY_INTERVAL = 3


def wait_for_thingsboard_and_login():
    """Poll the login endpoint until ThingsBoard is actually ready to
    accept API calls (container 'started' != application ready)."""
    deadline = time.time() + MAX_WAIT_SECONDS
    last_error = None

    while time.time() < deadline:
        try:
            resp = requests.post(
                f"{TB_HOST}/api/auth/login",
                json={"username": TB_ADMIN_EMAIL, "password": TB_ADMIN_PASSWORD},
                timeout=5,
            )
            if resp.status_code == 200:
                return resp.json()["token"]
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text}"
        except requests.exceptions.RequestException as e:
            last_error = str(e)

        print(f"[WAIT] ThingsBoard not ready yet ({last_error}), retrying...")
        time.sleep(RETRY_INTERVAL)

    print(f"[ERROR] Gave up waiting for ThingsBoard: {last_error}")
    sys.exit(1)


def auth_headers(token):
    return {"X-Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def find_existing_rule_chain_id(token, name):
    resp = requests.get(
        f"{TB_HOST}/api/ruleChains",
        params={"pageSize": 100, "page": 0, "type": "CORE"},
        headers=auth_headers(token),
        timeout=10,
    )
    resp.raise_for_status()
    for rc in resp.json().get("data", []):
        if rc.get("name") == name:
            return rc["id"]["id"]
    return None


def import_rule_chain(token, filepath):
    with open(filepath) as f:
        exported = json.load(f)

    rule_chain = exported["ruleChain"]
    metadata = exported["metadata"]
    name = rule_chain["name"]

    existing_id = find_existing_rule_chain_id(token, name)
    if existing_id:
        print(f"[RULE CHAIN] '{name}' already exists, updating...")
        rule_chain["id"] = {"id": existing_id, "entityType": "RULE_CHAIN"}
    else:
        print(f"[RULE CHAIN] '{name}' not found, creating...")
        rule_chain.pop("id", None)

    resp = requests.post(
        f"{TB_HOST}/api/ruleChain",
        headers=auth_headers(token),
        json=rule_chain,
        timeout=15,
    )
    resp.raise_for_status()
    saved = resp.json()
    rule_chain_id = saved["id"]["id"]

    metadata["ruleChainId"] = {"id": rule_chain_id, "entityType": "RULE_CHAIN"}
    resp = requests.post(
        f"{TB_HOST}/api/ruleChain/metadata",
        headers=auth_headers(token),
        json=metadata,
        timeout=15,
    )
    resp.raise_for_status()

    print(f"[RULE CHAIN] '{name}' imported successfully (id={rule_chain_id}).")
    if not saved.get("root", False):
        print(
            f"[NOTE] '{name}' is not a root rule chain. On a brand-new "
            f"ThingsBoard instance, you still need to either (a) add a "
            f"'Rule Chain' node in your root chain pointing to it, or "
            f"(b) assign it as a device profile's default rule chain, "
            f"so telemetry actually reaches it."
        )


def find_existing_dashboard_id(token, title):
    resp = requests.get(
        f"{TB_HOST}/api/tenant/dashboards",
        params={"pageSize": 100, "page": 0},
        headers=auth_headers(token),
        timeout=10,
    )
    resp.raise_for_status()
    for d in resp.json().get("data", []):
        if d.get("title") == title:
            return d["id"]["id"]
    return None


def import_dashboard(token, filepath):
    with open(filepath) as f:
        dashboard = json.load(f)

    # Some exports wrap the dashboard in {"dashboard": {...}}; handle both.
    if "dashboard" in dashboard and "title" not in dashboard:
        dashboard = dashboard["dashboard"]

    title = dashboard["title"]
    existing_id = find_existing_dashboard_id(token, title)
    if existing_id:
        print(f"[DASHBOARD] '{title}' already exists, updating...")
        dashboard["id"] = {"id": existing_id, "entityType": "DASHBOARD"}
    else:
        print(f"[DASHBOARD] '{title}' not found, creating...")
        dashboard.pop("id", None)

    resp = requests.post(
        f"{TB_HOST}/api/dashboard",
        headers=auth_headers(token),
        json=dashboard,
        timeout=15,
    )
    resp.raise_for_status()
    print(f"[DASHBOARD] '{title}' imported successfully.")


def main():
    print(f"[INFO] Connecting to ThingsBoard at {TB_HOST}...")
    token = wait_for_thingsboard_and_login()
    print("[INFO] Logged in successfully.")

    rule_chain_files = sorted(glob.glob(os.path.join(RULE_CHAINS_DIR, "*.json")))
    dashboard_files = sorted(glob.glob(os.path.join(DASHBOARDS_DIR, "*.json")))

    if not rule_chain_files and not dashboard_files:
        print("[INFO] No rule chain or dashboard JSON files found. Nothing to do.")
        return

    for filepath in rule_chain_files:
        try:
            import_rule_chain(token, filepath)
        except Exception as e:
            print(f"[ERROR] Failed to import rule chain '{filepath}': {e}")

    for filepath in dashboard_files:
        try:
            import_dashboard(token, filepath)
        except Exception as e:
            print(f"[ERROR] Failed to import dashboard '{filepath}': {e}")

    print("[INFO] Import complete.")


if __name__ == "__main__":
    main()