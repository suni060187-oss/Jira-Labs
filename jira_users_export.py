import csv
import sys
import time
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

# ============================================================
# CONFIGURATION
# ============================================================

JIRA_BASE_URL = "http://48.200.96.84:8080/"
JIRA_USERNAME = "admin"
JIRA_PASSWORD = "admin"

OUTPUT_CSV = "jira_users_export.csv"

# If your Jira uses a self-signed cert, set this to False
VERIFY_SSL = True

# Pagination size for user search
PAGE_SIZE = 100

# Small delay between requests
REQUEST_DELAY_SECONDS = 0.1


# ============================================================
# SESSION
# ============================================================

session = requests.Session()
session.auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_PASSWORD)
session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json",
})
session.verify = VERIFY_SSL


# ============================================================
# HELPERS
# ============================================================

def api_get(path: str, params: Optional[dict] = None, expected=(200,)):
    url = f"{JIRA_BASE_URL.rstrip('/')}{path}"
    resp = session.get(url, params=params, timeout=60)
    time.sleep(REQUEST_DELAY_SECONDS)

    if resp.status_code not in expected:
        raise RuntimeError(
            f"GET {resp.url} failed with status {resp.status_code}: {resp.text[:1000]}"
        )

    if not resp.text.strip():
        return {}

    return resp.json()


def get_all_users() -> List[dict]:
    """
    Pull users using Jira Server/DC user search pagination.
    This retrieves all users visible to the authenticated account.
    """
    users = []
    start_at = 0

    while True:
        data = api_get(
            "/rest/api/2/user/search",
            params={
                "username": ".",      # broad match to return visible users
                "startAt": start_at,
                "maxResults": PAGE_SIZE,
                "includeActive": "true",
                "includeInactive": "true",
            },
            expected=(200,)
        )

        if not isinstance(data, list):
            raise RuntimeError("Unexpected response from /rest/api/2/user/search")

        if not data:
            break

        users.extend(data)

        if len(data) < PAGE_SIZE:
            break

        start_at += PAGE_SIZE

    return users


def get_user_details(username: Optional[str] = None, key: Optional[str] = None) -> dict:
    """
    Get a single user's details with groups expanded.
    """
    params = {"expand": "groups"}
    if username:
        params["username"] = username
    elif key:
        params["key"] = key
    else:
        raise ValueError("Either username or key must be provided")

    return api_get("/rest/api/2/user", params=params, expected=(200,))


def extract_groups(user_detail: dict) -> str:
    groups_obj = user_detail.get("groups", {})
    group_items = groups_obj.get("items", []) if isinstance(groups_obj, dict) else []

    names = []
    for g in group_items:
        name = g.get("name")
        if name:
            names.append(name)

    names = sorted(set(names))
    return ";".join(names)


def pick_username(user_obj: dict) -> str:
    # Jira Server/DC usually returns "name"
    return user_obj.get("name", "")


def pick_user_id(user_obj: dict) -> str:
    # Different versions may expose key/name differently
    # We export both if available, preferring key as id column if present
    return user_obj.get("key") or user_obj.get("name") or ""


# ============================================================
# MAIN
# ============================================================

def main():
    print("Connecting to Jira and downloading users...")
    users = get_all_users()
    print(f"Users returned by search: {len(users)}")

    export_rows: List[Dict[str, str]] = []
    processed = 0

    for user in users:
        username = pick_username(user)
        user_key = user.get("key", "")

        if not username and not user_key:
            continue

        try:
            detail = get_user_details(username=username if username else None,
                                      key=None if username else user_key)
        except Exception as ex:
            export_rows.append({
                "username": username,
                "full_name": user.get("displayName", ""),
                "email": user.get("emailAddress", ""),
                "id": pick_user_id(user),
                "groups": "",
                "status": f"FAILED_TO_FETCH_GROUPS: {ex}",
            })
            continue

        export_rows.append({
            "username": detail.get("name", username),
            "full_name": detail.get("displayName", user.get("displayName", "")),
            "email": detail.get("emailAddress", user.get("emailAddress", "")),
            "id": pick_user_id(detail),
            "groups": extract_groups(detail),
            "status": "OK",
        })

        processed += 1
        if processed % 50 == 0:
            print(f"Processed {processed} users...")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["username", "full_name", "email", "id", "groups", "status"]
        )
        writer.writeheader()
        writer.writerows(export_rows)

    print(f"Done. Exported {len(export_rows)} rows to {OUTPUT_CSV}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)