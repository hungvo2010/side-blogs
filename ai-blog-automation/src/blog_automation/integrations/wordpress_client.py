"""WordPress REST API client for publishing.

Provides WordPress integration for creating posts, uploading media,
and managing content.
"""

import base64
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests

from blog_automation.config import get_settings
from blog_automation.errors import (
    APIAuthenticationError,
    APIInvalidResponseError,
    PublishingFailureError,
)
from blog_automation.integrations.base_client import HTTPClient
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class WordPressClient(HTTPClient):
    """WordPress REST API client.

    Provides methods for:
    - Creating and updating posts
    - Uploading media
    - Managing categories and tags
    - Setting custom fields (ACF)
    """

    def __init__(
        self,
        site_url: str | None = None,
        username: str | None = None,
        app_password: str | None = None,
    ):
        """Initialize WordPress client.

        Args:
            site_url: WordPress site URL
            username: WordPress username
            app_password: WordPress application password
        """
        settings = get_settings()
        self.site_url = (site_url or settings.wordpress_url).rstrip("/")
        self.username = username or settings.wordpress_username
        self.app_password = app_password or settings.wordpress_app_password

        if not all([self.site_url, self.username, self.app_password]):
            raise APIAuthenticationError(
                message="WordPress credentials not configured",
                service="wordpress",
            )

        # WordPress REST API base URL
        api_url = urljoin(self.site_url, "/wp-json/wp/v2")

        super().__init__(
            base_url=api_url,
            timeout=60,
            max_retries=3,
            rate_limit=30,
        )

        # Set up Basic Auth
        credentials = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.set_auth_header("Authorization", f"Basic {encoded}")

        logger.info("WordPress client initialized", site=self.site_url)

    def create_post(
        self,
        title: str,
        content: str,
        status: str = "draft",
        excerpt: str | None = None,
        categories: list[int] | None = None,
        tags: list[int] | None = None,
        featured_media: int | None = None,
        slug: str | None = None,
        meta: dict | None = None,
        date: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a new WordPress post.

        Args:
            title: Post title
            content: Post content (HTML)
            status: Post status (draft, publish, future, pending)
            excerpt: Post excerpt
            categories: List of category IDs
            tags: List of tag IDs
            featured_media: Featured image attachment ID
            slug: URL slug
            meta: Custom meta fields
            date: Publication date (for scheduled posts)

        Returns:
            Created post data
        """
        payload = {
            "title": title,
            "content": content,
            "status": status,
        }

        if excerpt:
            payload["excerpt"] = excerpt
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        if featured_media:
            payload["featured_media"] = featured_media
        if slug:
            payload["slug"] = slug
        if meta:
            payload["meta"] = meta
        if date:
            payload["date"] = date.isoformat()

        try:
            response = self.post("posts", json=payload)

            logger.info(
                "WordPress post created",
                post_id=response.get("id"),
                status=status,
            )

            return {
                "id": response.get("id"),
                "link": response.get("link"),
                "slug": response.get("slug"),
                "status": response.get("status"),
                "title": response.get("title", {}).get("rendered"),
            }

        except Exception as e:
            raise PublishingFailureError(
                message=f"Failed to create WordPress post: {str(e)}",
                context={"title": title, "status": status},
            ) from e

    def update_post(
        self,
        post_id: int,
        **kwargs,
    ) -> dict[str, Any]:
        """Update an existing WordPress post.

        Args:
            post_id: Post ID to update
            **kwargs: Fields to update

        Returns:
            Updated post data
        """
        try:
            response = self.post(f"posts/{post_id}", json=kwargs)

            logger.info("WordPress post updated", post_id=post_id)

            return {
                "id": response.get("id"),
                "link": response.get("link"),
                "status": response.get("status"),
            }

        except Exception as e:
            raise PublishingFailureError(
                message=f"Failed to update WordPress post: {str(e)}",
                context={"post_id": post_id},
            ) from e

    def get_post(self, post_id: int) -> dict[str, Any]:
        """Get a WordPress post by ID.

        Args:
            post_id: Post ID

        Returns:
            Post data
        """
        response = self.get(f"posts/{post_id}")
        return response

    def delete_post(self, post_id: int, force: bool = False) -> bool:
        """Delete a WordPress post.

        Args:
            post_id: Post ID
            force: Skip trash and permanently delete

        Returns:
            True if deleted
        """
        params = {"force": force}
        self.delete(f"posts/{post_id}", params=params)
        logger.info("WordPress post deleted", post_id=post_id)
        return True

    def upload_media(
        self,
        file_path: str | None = None,
        file_data: bytes | None = None,
        filename: str = "image.jpg",
        title: str | None = None,
        alt_text: str | None = None,
        caption: str | None = None,
    ) -> dict[str, Any]:
        """Upload media to WordPress.

        Args:
            file_path: Path to file to upload
            file_data: Raw file bytes (alternative to file_path)
            filename: Filename for the upload
            title: Media title
            alt_text: Alt text for images
            caption: Media caption

        Returns:
            Uploaded media data with attachment ID
        """
        if file_path:
            with open(file_path, "rb") as f:
                file_data = f.read()

        if not file_data:
            raise APIInvalidResponseError(
                message="No file data provided",
                service="wordpress",
            )

        # Determine content type
        content_type = "image/jpeg"
        if filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith(".gif"):
            content_type = "image/gif"
        elif filename.endswith(".webp"):
            content_type = "image/webp"

        headers = {
            "Content-Type": content_type,
            "Content-Disposition": f'attachment; filename="{filename}"',
        }

        try:
            response = self.request(
                "POST",
                "media",
                data=file_data,
                headers=headers,
            )

            media_id = response.get("id")

            # Update media metadata if provided
            if any([title, alt_text, caption]):
                meta_update = {}
                if title:
                    meta_update["title"] = title
                if alt_text:
                    meta_update["alt_text"] = alt_text
                if caption:
                    meta_update["caption"] = caption

                self.post(f"media/{media_id}", json=meta_update)

            logger.info("WordPress media uploaded", media_id=media_id)

            return {
                "id": media_id,
                "url": response.get("source_url"),
                "title": response.get("title", {}).get("rendered"),
            }

        except Exception as e:
            raise PublishingFailureError(
                message=f"Failed to upload media: {str(e)}",
                context={"filename": filename},
            ) from e

    def upload_media_from_url(
        self,
        image_url: str,
        filename: str | None = None,
        alt_text: str | None = None,
    ) -> dict[str, Any]:
        """Download and upload media from URL.

        Args:
            image_url: URL of image to download
            filename: Optional filename override
            alt_text: Alt text for the image

        Returns:
            Uploaded media data
        """
        # Download image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        if not filename:
            filename = image_url.split("/")[-1].split("?")[0]
            if not filename:
                filename = "image.jpg"

        return self.upload_media(
            file_data=response.content,
            filename=filename,
            alt_text=alt_text,
        )

    def update_post_meta(
        self,
        post_id: int,
        meta: dict[str, Any],
    ) -> bool:
        """Update post custom fields (ACF compatible).

        Args:
            post_id: Post ID
            meta: Dictionary of meta fields

        Returns:
            True if updated
        """
        # Try ACF endpoint first
        try:
            acf_url = f"{self.site_url}/wp-json/acf/v3/posts/{post_id}"
            response = requests.post(
                acf_url,
                json={"fields": meta},
                headers=self.session.headers,
                timeout=30,
            )
            if response.ok:
                logger.info("ACF fields updated", post_id=post_id)
                return True
        except Exception:
            pass

        # Fallback to standard meta
        self.post(f"posts/{post_id}", json={"meta": meta})
        logger.info("Post meta updated", post_id=post_id)
        return True

    def get_categories(self) -> list[dict[str, Any]]:
        """Get all categories.

        Returns:
            List of category data
        """
        response = self.get("categories", params={"per_page": 100})
        return [
            {
                "id": cat.get("id"),
                "name": cat.get("name"),
                "slug": cat.get("slug"),
            }
            for cat in response
        ]

    def get_tags(self) -> list[dict[str, Any]]:
        """Get all tags.

        Returns:
            List of tag data
        """
        response = self.get("tags", params={"per_page": 100})
        return [
            {
                "id": tag.get("id"),
                "name": tag.get("name"),
                "slug": tag.get("slug"),
            }
            for tag in response
        ]

    def create_category(self, name: str, slug: str | None = None) -> dict[str, Any]:
        """Create a new category.

        Args:
            name: Category name
            slug: URL slug

        Returns:
            Created category data
        """
        payload = {"name": name}
        if slug:
            payload["slug"] = slug

        response = self.post("categories", json=payload)
        return {
            "id": response.get("id"),
            "name": response.get("name"),
            "slug": response.get("slug"),
        }

    def create_tag(self, name: str, slug: str | None = None) -> dict[str, Any]:
        """Create a new tag.

        Args:
            name: Tag name
            slug: URL slug

        Returns:
            Created tag data
        """
        payload = {"name": name}
        if slug:
            payload["slug"] = slug

        response = self.post("tags", json=payload)
        return {
            "id": response.get("id"),
            "name": response.get("name"),
            "slug": response.get("slug"),
        }

    def schedule_post(
        self,
        post_id: int,
        publish_date: datetime,
    ) -> dict[str, Any]:
        """Schedule a post for future publication.

        Args:
            post_id: Post ID
            publish_date: When to publish

        Returns:
            Updated post data
        """
        return self.update_post(
            post_id,
            status="future",
            date=publish_date.isoformat(),
        )

    def publish_post(self, post_id: int) -> dict[str, Any]:
        """Immediately publish a post.

        Args:
            post_id: Post ID

        Returns:
            Updated post data
        """
        return self.update_post(post_id, status="publish")

    def test_connection(self) -> bool:
        """Test WordPress connection.

        Returns:
            True if connection successful
        """
        try:
            self.get("users/me")
            logger.info("WordPress connection test successful")
            return True
        except Exception as e:
            logger.error(f"WordPress connection test failed: {e}")
            return False
