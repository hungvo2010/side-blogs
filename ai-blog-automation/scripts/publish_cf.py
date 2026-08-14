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

import base64
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
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
BRANCH = os.environ.get("CLOUDFLARE_DEPLOY_BRANCH", "main")

API = "https://api.cloudflare.com/client/v4"
PROJECT_URL = f"{API}/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT}"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def _content_type(path: str) -> str:
    t, _ = mimetypes.guess_type(path)
    return t or "application/octet-stream"


# ─── Build ───────────────────────────────────────────────────────────────
def build_site() -> None:
    """Run publish.py to build static HTML in public/."""
    publish_py = Path(__file__).resolve().parent / "publish.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_SRC)
    subprocess.run([sys.executable, str(publish_py)], env=env, check=True)


# ─── Upload ──────────────────────────────────────────────────────────────
def upload() -> str:
    """Direct Upload public/ to Cloudflare Pages (manifest API). Returns deployment URL.

    Replicates ``wrangler pages deploy``: upload-token → check-missing →
    assets/upload → upsert-hashes → create deployment.
    Manifest keys use leading slashes (``/index.html``) and **MD5** hashes —
    Cloudflare's asset store rejects SHA1/relative keys (files 404/500).
    """
    files: dict[str, bytes] = {}
    for root, _dirs, fnames in os.walk(PUBLIC_DIR):
        for fname in fnames:
            full = Path(root) / fname
            files[full.relative_to(PUBLIC_DIR).as_posix()] = full.read_bytes()
    if not files:
        raise RuntimeError("public/ is empty, nothing to deploy")

    # 1. Upload JWT
    r = requests.get(f"{PROJECT_URL}/upload-token", headers=HEADERS, timeout=60)
    r.raise_for_status()
    jwt = r.json()["result"]["jwt"]
    uh = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}

    # 2. Manifest (path → md5) + upload payload (base64)
    manifest = {"/" + p: hashlib.md5(d).hexdigest() for p, d in sorted(files.items())}
    payload = [
        {
            "key": hashlib.md5(d).hexdigest(),
            "value": base64.b64encode(d).decode(),
            "metadata": {"contentType": _content_type(p)},
            "base64": True,
        }
        for p, d in sorted(files.items())
    ]

    # 3. Only upload hashes Cloudflare doesn't already have
    try:
        r = requests.post(
            f"{API}/pages/assets/check-missing",
            headers=uh,
            json={"hashes": list(manifest.values())},
            timeout=60,
        )
        r.raise_for_status()
        missing = set(r.json().get("result") or [])
    except Exception as e:
        print(f"check-missing failed ({e}), uploading all")
        missing = set()
    to_upload = [p for p in payload if p["key"] in missing] or payload
    print(f"Uploading {len(to_upload)}/{len(payload)} files")

    # 4. Upload (batched)
    for i in range(0, len(to_upload), 200):
        batch = to_upload[i : i + 200]
        r = requests.post(
            f"{API}/pages/assets/upload",
            headers=uh,
            data=json.dumps(batch),
            timeout=600,
        )
        r.raise_for_status()
        res = r.json()
        if not res.get("success") or res.get("result", {}).get("unsuccessful_keys"):
            raise RuntimeError(f"upload failed: {r.text[:400]}")

    # 5. Register hashes
    r = requests.post(
        f"{API}/pages/assets/upsert-hashes",
        headers=uh,
        json={"hashes": list(manifest.values())},
        timeout=60,
    )
    r.raise_for_status()

    # 6. Create deployment
    r = requests.post(
        f"{PROJECT_URL}/deployments",
        headers=HEADERS,
        files={
            "branch": (None, BRANCH),
            "manifest": (None, json.dumps(manifest), "application/json"),
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Cloudflare deploy failed: {r.status_code} {r.text[:300]}")
    deployment = r.json()["result"]

    url = f"https://dash.cloudflare.com/{ACCOUNT_ID}/pages/view/{PROJECT}/{deployment['id']}"
    print(f"🚀 Deployed: https://{deployment['short_id']}.{PROJECT}.pages.dev")
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
