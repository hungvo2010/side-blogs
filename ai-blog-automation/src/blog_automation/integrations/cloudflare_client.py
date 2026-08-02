"""Cloudflare API client for Pages deployments and R2 media storage.

Replaces the WordPress publishing layer for static-site workflows.
No credentials needed for the GitHub-driven flow (Cloudflare Pages can
connect to a GitHub repo directly).  The API client is useful for:

- Direct Upload deploys (skip the GitHub integration entirely)
- R2 bucket management (store images/media)
- Custom domain / DNS management
- Cache purging after deploys

API docs: https://developers.cloudflare.com/api/
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests

from blog_automation.config import get_settings
from blog_automation.errors import (
    APIAuthenticationError,
    PublishingFailureError,
)
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class CloudflareClient:
    """Cloudflare API client for Pages and R2."""

    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(
        self,
        api_token: str | None = None,
        account_id: str | None = None,
        project_name: str | None = None,
    ):
        settings = get_settings()
        self.api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.project_name = project_name or os.getenv("CLOUDFLARE_PROJECT_NAME", "")

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
        )

    @property
    def _pages_url(self) -> str:
        return f"{self.BASE_URL}/accounts/{self.account_id}/pages/projects"

    # ------------------------------------------------------------------
    # Pages: Direct Upload (no GitHub needed)
    # ------------------------------------------------------------------
    def create_project(
        self, name: str, production_branch: str = "main"
    ) -> dict[str, Any]:
        """Create a Cloudflare Pages project."""
        r = self._session.post(
            self._pages_url,
            json={"name": name, "production_branch": production_branch},
        )
        self._check(r, "create Pages project")
        return r.json()["result"]

    def get_deployment_status(self, project: str, deployment_id: str) -> dict:
        """Poll deployment status."""
        url = f"{self._pages_url}/{project}/deployments/{deployment_id}"
        r = self._session.get(url)
        self._check(r, "get deployment status")
        return r.json()["result"]

    def upload_deployment(
        self,
        project: str,
        dist_dir: Path,
        branch: str = "main",
    ) -> dict:
        """Direct Upload a static site to Cloudflare Pages.

        This bypasses the GitHub integration entirely - zip the output
        dir and upload to the Pages API directly.
        """
        import tempfile
        import zipfile

        # 1. Zip the dist dir
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        try:
            with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _dirs, files in os.walk(dist_dir):
                    for fname in files:
                        full = Path(root) / fname
                        arcname = full.relative_to(dist_dir)
                        zf.write(full, str(arcname))
        finally:
            tmp.close()

        # 2. Request upload URL
        r = self._session.post(
            f"{self._pages_url}/{project}/deployments",
            json={"branch": branch},
        )
        self._check(r, "request deployment URL")
        deployment = r.json()["result"]

        # 3. Upload zip to the presigned URL
        with open(tmp.name, "rb") as f:
            r2 = requests.post(
                deployment["upload_url"],
                headers={"Content-Type": "application/zip"},
                data=f,
            )

        os.unlink(tmp.name)

        if r2.status_code not in (200, 201, 204):
            raise PublishingFailureError(
                message=f"Upload to Cloudflare failed: {r2.status_code} {r2.text[:200]}",
                context={"project": project},
            )

        logger.info(
            "Deployment uploaded to Cloudflare Pages",
            project=project,
            deployment_id=deployment["id"],
        )
        return deployment

    # ------------------------------------------------------------------
    # R2 (media / bucket storage)
    # ------------------------------------------------------------------
    def r2_upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload a file to an R2 bucket. Returns public URL."""
        r = self._session.put(
            f"{self.BASE_URL}/accounts/{self.account_id}/r2/buckets/{bucket}/objects/{key}",
            data=data,
            headers={"Content-Type": content_type},
        )
        self._check(r, "R2 upload")
        # Public URL depends on custom domain or r2.dev
        return f"https://pub-{self.account_id}.r2.dev/{key}"

    # ------------------------------------------------------------------
    # Cache purge
    # ------------------------------------------------------------------
    def purge_cache(self, files: list[str] | None = None) -> bool:
        """Purge Cloudflare cache."""
        zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "")
        url = f"{self.BASE_URL}/zones/{zone_id}/purge_cache"
        payload: dict = {"purge_everything": True} if not files else {"files": files}
        r = self._session.post(url, json=payload)
        self._check(r, "purge cache")
        return True

    def _check(self, r: requests.Response, context: str) -> None:
        if r.status_code == 401:
            raise APIAuthenticationError(
                message="Cloudflare API token invalid or expired",
                service="cloudflare",
            )
        if r.status_code >= 400:
            raise PublishingFailureError(
                message=f"Cloudflare {context} failed: {r.status_code} {r.text[:200]}",
                context={"status": r.status_code},
            )
