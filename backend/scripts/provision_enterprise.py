"""CLI: provision enterprise tenant for dogfood.

Usage (from backend/):
  uv run python -m scripts.provision_enterprise \\
    --company "Acme Sales" --slug acme-sales --admin-email you@company.com
"""

import argparse
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision enterprise tenant via ops API")
    parser.add_argument("--api", default="http://127.0.0.1:8006", help="API base URL")
    parser.add_argument("--company", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--seat-limit", type=int, default=None)
    parser.add_argument("--ops-token", default=None, help="X-Ops-Token if ENTERPRISE_OPS_TOKEN set")
    args = parser.parse_args()

    headers = {}
    if args.ops_token:
        headers["X-Ops-Token"] = args.ops_token

    body = {
        "company_name": args.company,
        "slug": args.slug,
        "admin_email": args.admin_email,
        "seat_limit": args.seat_limit,
    }
    url = f"{args.api.rstrip('/')}/api/v1/ops/enterprise/provision"
    with httpx.Client(timeout=30.0) as client:
        r = client.post(url, json=body, headers=headers)
    if r.status_code >= 400:
        print(r.status_code, r.text, file=sys.stderr)
        sys.exit(1)
    data = r.json()
    print(f"OK org_id={data['org_id']} slug={data['slug']} admin={data['primary_admin_user_id']}")


if __name__ == "__main__":
    main()
