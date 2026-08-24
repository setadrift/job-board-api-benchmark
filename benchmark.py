#!/usr/bin/env python3
"""Measure public ATS list APIs with one transparent, repeatable test rig."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "job-board-api-benchmark/1.0 (+https://github.com/setadrift/job-board-api-benchmark)"
TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Provider:
    name: str
    family: str
    endpoint: str


PROVIDERS = (
    Provider("GitLab", "Greenhouse", "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs?content=true"),
    Provider("SearchApi", "Ashby", "https://api.ashbyhq.com/posting-api/job-board/searchapi?includeCompensation=true"),
    Provider("Palantir", "Lever", "https://api.lever.co/v0/postings/palantir?mode=json"),
    Provider("ServiceNow", "SmartRecruiters", "https://api.smartrecruiters.com/v1/companies/ServiceNow/postings"),
)


def request_bytes(url: str) -> tuple[bytes, int, float]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        payload = response.read()
        status = response.status
    return payload, status, (time.perf_counter() - started) * 1000


def check_url(url: str) -> int | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Range": "bytes=0-1024"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response.read(1024)
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (urllib.error.URLError, TimeoutError):
        return None


def extract_records(family: str, payload: Any) -> list[dict[str, Any]]:
    if family == "Greenhouse":
        return list(payload.get("jobs", []))
    if family == "Ashby":
        return list(payload.get("jobs", []))
    if family == "Lever":
        return list(payload)
    if family == "SmartRecruiters":
        return list(payload.get("content", []))
    raise ValueError(f"Unsupported family: {family}")


def normalize_record(family: str, record: dict[str, Any]) -> dict[str, Any]:
    if family == "Greenhouse":
        return {
            "id": record.get("id"),
            "title": record.get("title"),
            "location": (record.get("location") or {}).get("name"),
            "published_at": record.get("first_published") or record.get("updated_at"),
            "application_url": record.get("absolute_url"),
        }
    if family == "Ashby":
        return {
            "id": record.get("id"),
            "title": record.get("title"),
            "location": record.get("location"),
            "published_at": record.get("publishedAt"),
            "application_url": record.get("applyUrl") or record.get("jobUrl"),
        }
    if family == "Lever":
        return {
            "id": record.get("id"),
            "title": record.get("text"),
            "location": (record.get("categories") or {}).get("location"),
            "published_at": record.get("createdAt"),
            "application_url": record.get("applyUrl") or record.get("hostedUrl"),
        }
    if family == "SmartRecruiters":
        return {
            "id": record.get("id"),
            "title": record.get("name"),
            "location": (record.get("location") or {}).get("fullLocation"),
            "published_at": record.get("releasedDate"),
            # The list response exposes a detail API URL, not a candidate-facing URL.
            "application_url": record.get("postingUrl") or record.get("applyUrl"),
        }
    raise ValueError(f"Unsupported family: {family}")


def percentage(records: list[dict[str, Any]], field: str) -> float:
    if not records:
        return 0.0
    present = sum(value.get(field) not in (None, "", [], {}) for value in records)
    return round(100 * present / len(records), 2)


def duplicate_count(records: list[dict[str, Any]]) -> int:
    identifiers = [str(record["id"]) for record in records if record.get("id") is not None]
    return len(identifiers) - len(set(identifiers))


def benchmark_provider(provider: Provider, runs: int, link_sample: int) -> dict[str, Any]:
    latencies: list[float] = []
    statuses: list[int] = []
    last_payload = b""
    for _ in range(runs):
        last_payload, status, latency = request_bytes(provider.endpoint)
        statuses.append(status)
        latencies.append(latency)

    parsed = json.loads(last_payload)
    raw_records = extract_records(provider.family, parsed)
    records = [normalize_record(provider.family, item) for item in raw_records]
    urls = [record["application_url"] for record in records if record.get("application_url")][:link_sample]
    link_statuses = [check_url(url) for url in urls]
    link_successes = sum(status is not None and 200 <= status < 400 for status in link_statuses)

    return {
        "provider": provider.name,
        "ats_family": provider.family,
        "endpoint": provider.endpoint,
        "runs": runs,
        "http_statuses": statuses,
        "latency_ms": {
            "min": round(min(latencies), 2),
            "median": round(statistics.median(latencies), 2),
            "max": round(max(latencies), 2),
        },
        "payload_bytes": len(last_payload),
        "payload_sha256": hashlib.sha256(last_payload).hexdigest(),
        "record_count": len(records),
        "duplicate_id_count": duplicate_count(records),
        "field_presence_pct": {
            field: percentage(records, field)
            for field in ("id", "title", "location", "published_at", "application_url")
        },
        "candidate_links": {
            "sampled": len(link_statuses),
            "successful": link_successes,
            "success_pct": round(100 * link_successes / len(link_statuses), 2) if link_statuses else None,
            "statuses": link_statuses,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    rows = []
    for item in result["providers"]:
        fields = item["field_presence_pct"]
        links = item["candidate_links"]
        link_value = "n/a" if links["success_pct"] is None else f'{links["success_pct"]:.0f}%'
        rows.append(
            f'| {item["ats_family"]} ({item["provider"]}) | {item["record_count"]} | '
            f'{item["latency_ms"]["median"]:.1f} | {fields["location"]:.0f}% | '
            f'{fields["published_at"]:.0f}% | {fields["application_url"]:.0f}% | '
            f'{item["duplicate_id_count"]} | {link_value} |'
        )
    table = "\n".join(rows)
    return f"""# Public job-board API benchmark

Measured at **{result['measured_at']}** using {result['runs_per_provider']} sequential requests per list endpoint.

| ATS and test board | Records | Median latency (ms) | Location present | Published date present | Candidate URL in list | Duplicate IDs | Sampled links reachable |
|---|---:|---:|---:|---:|---:|---:|---:|
{table}

## What this result means

This is a comparison of four **specific public job-board list endpoints**, not a universal ranking of the ATS products. The company boards differ in size and geography, network conditions vary, and SmartRecruiters intentionally requires a detail request before returning a candidate-facing URL; its list-response score should not be read as a product defect.

## Reproduce it

```bash
python benchmark.py --runs {result['runs_per_provider']} --link-sample {result['link_sample']}
```

The command rewrites `results/latest.json`, appends a dated history snapshot, and regenerates this report. Raw third-party job descriptions are not republished; each result stores normalized aggregates plus a SHA-256 digest of the received payload.

## Method and limitations

- Requests run sequentially from one machine with the same timeout and user agent.
- Median latency is descriptive, not a controlled infrastructure benchmark.
- Field presence measures the list response only; it does not judge fields available through detail endpoints.
- Candidate-link checks sample the first available URLs and treat HTTP 200-399 as reachable.
- Public endpoints can change or rate-limit without notice. Re-measure before relying on the values.
"""


def run(runs: int, link_sample: int) -> dict[str, Any]:
    measured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "schema_version": 1,
        "measured_at": measured_at,
        "runs_per_provider": runs,
        "link_sample": link_sample,
        "providers": [benchmark_provider(provider, runs, link_sample) for provider in PROVIDERS],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--link-sample", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.runs < 1 or args.link_sample < 0:
        parser.error("--runs must be >= 1 and --link-sample must be >= 0")

    result = run(args.runs, args.link_sample)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    history_dir = args.output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    latest_path = args.output_dir / "latest.json"
    dated_path = history_dir / f'{result["measured_at"][:10]}.json'
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    latest_path.write_text(serialized, encoding="utf-8")
    dated_path.write_text(serialized, encoding="utf-8")
    Path("REPORT.md").write_text(render_report(result), encoding="utf-8")
    print(f"wrote {latest_path}, {dated_path}, and REPORT.md")


if __name__ == "__main__":
    main()
