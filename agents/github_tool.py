"""Direct GitHub API client for MCP-style tool functionality.

Bypasses Snowflake MCP OAuth limitations by calling GitHub REST API directly.
Used by both the primary chat agent (patch lookups) and the ontology monitor agent.
"""
import os
import httpx
from typing import Optional


GITHUB_ORG = os.getenv("GITHUB_ORG", "gduma-phData")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def search_repos(query: str, org: str = None) -> list[dict]:
    """Search GitHub repos matching a query within the org."""
    org = org or GITHUB_ORG
    search_q = f"{query} org:{org}"
    resp = httpx.get(
        "https://api.github.com/search/repositories",
        params={"q": search_q, "per_page": 20, "sort": "updated"},
        headers=_headers(),
        timeout=15.0,
    )
    if resp.status_code != 200:
        return []
    items = resp.json().get("items", [])
    return [
        {
            "name": r["name"],
            "full_name": r["full_name"],
            "description": r.get("description", ""),
            "url": r["html_url"],
            "updated_at": r.get("updated_at", ""),
        }
        for r in items
    ]


def get_repo_readme(repo_name: str, org: str = None) -> Optional[str]:
    """Get the README content of a repo."""
    org = org or GITHUB_ORG
    resp = httpx.get(
        f"https://api.github.com/repos/{org}/{repo_name}/readme",
        headers={**_headers(), "Accept": "application/vnd.github.raw+json"},
        timeout=10.0,
    )
    if resp.status_code == 200:
        return resp.text
    return None


def get_file_content(repo_name: str, path: str, org: str = None) -> Optional[str]:
    """Get raw file content from a repo."""
    org = org or GITHUB_ORG
    resp = httpx.get(
        f"https://api.github.com/repos/{org}/{repo_name}/contents/{path}",
        headers={**_headers(), "Accept": "application/vnd.github.raw+json"},
        timeout=10.0,
    )
    if resp.status_code == 200:
        return resp.text
    return None


def list_repo_files(repo_name: str, path: str = "", org: str = None) -> list[str]:
    """List files in a repo directory."""
    org = org or GITHUB_ORG
    resp = httpx.get(
        f"https://api.github.com/repos/{org}/{repo_name}/contents/{path}",
        headers=_headers(),
        timeout=10.0,
    )
    if resp.status_code != 200:
        return []
    items = resp.json()
    if not isinstance(items, list):
        return []
    return [f["name"] for f in items if f.get("type") == "file"]


def search_patch_repos(cve_id: str = None) -> list[dict]:
    """Search for patch repos, optionally filtered by CVE ID."""
    query = f"patch-CVE" if not cve_id else f"patch-{cve_id}"
    return search_repos(query)


def search_ontology_repos() -> list[dict]:
    """Search for ontology update repos."""
    return search_repos("ontology")


def get_patch_context(cve_ids: list[str] = None) -> str:
    """Get a formatted context string about patch repos for injection into agent prompts."""
    if cve_ids:
        repos = []
        for cve_id in cve_ids[:5]:
            repos.extend(search_patch_repos(cve_id))
    else:
        repos = search_patch_repos()

    if not repos:
        return "No patch repositories found matching the query."

    lines = [f"Found {len(repos)} patch repositories on GitHub ({GITHUB_ORG}):"]
    for r in repos[:10]:
        readme = get_repo_readme(r["name"])
        lines.append(f"\n--- {r['name']} ---")
        lines.append(f"URL: {r['url']}")
        lines.append(f"Updated: {r['updated_at']}")
        if readme:
            lines.append(f"README:\n{readme[:800]}")
    return "\n".join(lines)


def get_ontology_context() -> str:
    """Get formatted context about ontology repos for the monitoring agent."""
    repos = search_ontology_repos()
    if not repos:
        return "No ontology repositories found."

    lines = [f"Found {len(repos)} ontology update repositories on GitHub ({GITHUB_ORG}):"]
    for r in repos:
        lines.append(f"\n{'='*60}")
        lines.append(f"Repository: {r['name']}")
        lines.append(f"Description: {r['description']}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"Last Updated: {r['updated_at']}")

        # Read all markdown files
        files = list_repo_files(r["name"])
        md_files = [f for f in files if f.endswith(".md")]
        for md_file in md_files:
            content = get_file_content(r["name"], md_file)
            if content:
                lines.append(f"\n--- {md_file} ---")
                lines.append(content[:2000])

    return "\n".join(lines)
