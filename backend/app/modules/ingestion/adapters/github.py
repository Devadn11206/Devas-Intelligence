from datetime import datetime, timezone
from typing import Any, List, Optional
import httpx
from app.modules.ingestion.base import BaseSourceAdapter, CanonicalRecord
from app.db.models.intel import ContentType, Source


class GitHubAdapter(BaseSourceAdapter):
    """Adapter for GitHub Search and Repositories API."""

    async def fetch(self, config: dict[str, Any], since: Optional[datetime] = None) -> List[dict[str, Any]]:
        query = config.get("query", "topic:machine-learning topic:neural-networks")
        token = config.get("token") or config.get("github_token")

        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = "https://api.github.com/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(config.get("per_page", 20), 50),
        }

        resp = await self.client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])

        # Fetch README for top repositories if configured
        results = []
        for item in items:
            raw_readme = ""
            if config.get("fetch_readme", True):
                owner = item.get("owner", {}).get("login")
                repo = item.get("name")
                if owner and repo:
                    try:
                        readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
                        readme_resp = await self.client.get(readme_url, timeout=5.0)
                        if readme_resp.status_code == 200:
                            raw_readme = readme_resp.text[:10000]  # truncate to 10kb
                    except Exception:
                        pass

            item["readme_content"] = raw_readme
            results.append(item)

        return results

    def parse(self, raw_items: List[dict[str, Any]]) -> List[dict[str, Any]]:
        parsed = []
        for repo in raw_items:
            full_name = repo.get("full_name") or f"{repo.get('owner', {}).get('login')}/{repo.get('name')}"
            canonical_url = repo.get("html_url") or f"https://github.com/{full_name}"

            pub_date = datetime.now(timezone.utc)
            if repo.get("created_at"):
                try:
                    pub_date = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            license_name = repo.get("license", {}).get("name") if repo.get("license") else None

            parsed.append({
                "external_id": str(repo.get("id", full_name)),
                "canonical_url": canonical_url,
                "title": full_name,
                "summary_raw": repo.get("description") or "No description provided.",
                "content_raw": repo.get("readme_content") or repo.get("description") or "",
                "authors": [repo.get("owner", {}).get("login")] if repo.get("owner") else [],
                "tags": repo.get("topics", []) + ([repo.get("language")] if repo.get("language") else []),
                "published_at": pub_date,
                "metadata": {
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "open_issues": repo.get("open_issues_count", 0),
                    "language": repo.get("language"),
                    "license": license_name,
                    "default_branch": repo.get("default_branch", "main"),
                },
            })
        return parsed

    def normalize(self, parsed_items: List[dict[str, Any]], source: Source) -> List[CanonicalRecord]:
        records = []
        for item in parsed_items:
            records.append(
                CanonicalRecord(
                    external_id=item["external_id"],
                    canonical_url=item["canonical_url"],
                    content_type=ContentType.REPO,
                    title=item["title"],
                    summary_raw=item["summary_raw"],
                    content_raw=item["content_raw"],
                    authors=item.get("authors", []),
                    tags=[t for t in item.get("tags", []) if t],
                    metadata=item.get("metadata", {}),
                    published_at=item["published_at"],
                )
            )
        return records
