#!/usr/bin/env python3
"""Build static site → upload straight to Cloudflare Pages. No git needed.

Usage::

    python scripts/publish_cf.py                    # build all content/ → deploy
    python scripts/publish_cf.py post.md -t "Title" # single post → deploy

Env vars required:
    CLOUDFLARE_API_TOKEN   — API token with Pages:Edit
    CLOUDFLARE_ACCOUNT_ID  — Cloudflare account ID
    CLOUDFLARE_PROJECT_NAME — Pages project name

Get token: https://dash.cloudflare.com/profile/api-tokens
    → Create Token → Custom → Permissions: Cloudflare Pages → Edit → All accounts
"""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

# ─── Config ──────────────────────────────────────────────────────────────
_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))

PUBLIC_DIR = Path(__file__).resolve().parents[2] / "public"
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
PROJECT = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
SITE_URL = os.environ.get("SITE_URL", "https://side-blogs.pages.dev")

API_BASE = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/projects"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


# ─── Build ───────────────────────────────────────────────────────────────
def build_site() -> None:
    """Run publish.py to build static HTML in public/."""
    publish_py = Path(__file__).resolve().parent / "publish.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_SRC)
    import subprocess

    subprocess.run(["python3", str(publish_py)], env=env, check=True)


# ─── Upload ──────────────────────────────────────────────────────────────
def upload() -> str:
    """Zip public/ and upload to Cloudflare Pages. Returns deployment URL."""
    # 1. Zip public/
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(PUBLIC_DIR):
                for fname in files:
                    full = Path(root) / fname
                    zf.write(full, full.relative_to(PUBLIC_DIR))
    finally:
        tmp.close()

    # 2. Request deployment upload URL
    r = requests.post(
        f"{API_BASE}/{PROJECT}/deployments",
        headers=HEADERS,
        json={"branch": "main"},
    )
    r.raise_for_status()
    deployment = r.json()["result"]
    print(f"📦 Cloudflare deployment: {deployment['id'][:8]}...")

    # 3. Upload zip
    with open(tmp.name, "rb") as f:
        r2 = requests.post(
            deployment["upload_url"],
            headers={"Content-Type": "application/zip"},
            data=f,
        )
    os.unlink(tmp.name)

    if r2.status_code not in (200, 201, 204):
        print(f"❌ Upload failed: {r2.status_code} {r2.text[:300]}")
        sys.exit(1)

    url = f"https://dash.cloudflare.com/{ACCOUNT_ID}/pages/view/{PROJECT}/{deployment['id']}"
    print(f"🚀 Deployed! {url}")
    print(f"🌍 Live: {SITE_URL}")
    return url


# ─── CLI ─────────────────────────────────────────────────────────────────
def main():
    import argparse

    p = argparse.ArgumentParser(description="Build + deploy to Cloudflare Pages")
    p.add_argument("--no-build", action="store_true", help="Skip build, upload only")
    p.add_argument("--no-upload", action="store_true", help="Build only, skip upload")
    args = p.parse_args()

    if not args.no_build:
        print("🏗️  Building static site...")
        build_site()

    if not args.no_upload:
        print("📤 Uploading to Cloudflare Pages...")
        upload()

    print("✅ Done")


if __name__ == "__main__":
    main()
