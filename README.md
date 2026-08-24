# Job-board API benchmark

A small, reproducible benchmark of four public applicant-tracking-system list APIs: Greenhouse, Ashby, Lever, and SmartRecruiters.

The project asks a deliberately narrow question: **what does a developer receive from one public list request, how quickly does it arrive, and which decision-useful fields are actually present?** It does not scrape private data, republish job descriptions, or turn one company's board into a universal product ranking.

## Current result

See [REPORT.md](REPORT.md) for the latest measured table and [results/latest.json](results/latest.json) for the machine-readable result. The saved result includes payload hashes, counts, field-presence rates, latency observations, duplicate checks, and sampled candidate-link status codes.

## Run the benchmark

Requirements: Python 3.11+ and internet access. There are no third-party packages.

```bash
python -m unittest discover -s tests -v
python benchmark.py --runs 3 --link-sample 3
```

## Design choices

- **Same rig:** identical timeout, user agent, run count, and sequential request pattern.
- **No raw payload archive:** the benchmark stores aggregates and SHA-256 hashes, not third-party descriptions.
- **Explicit limitations:** list APIs differ by design. A missing list field may be available through a detail endpoint.
- **Remeasurement:** the scheduled workflow reruns weekly so the result can change when the APIs or boards change.
- **Inspectable code:** parsing and scoring logic live in one standard-library Python module with fixture-based tests.

## Repository map

```text
benchmark.py          request, normalization, measurement, and report generation
tests/                deterministic parser and metric tests
results/latest.json   latest machine-readable measurement
results/history/      dated snapshots for change-over-time analysis
REPORT.md             generated human-readable result and limitations
```

## Why I built this

Public job listings often look current in an API while the candidate journey is incomplete, stale, or shaped by a second endpoint. I wanted a compact example of evidence-first technical research: define a fair test, write the rig, preserve the result, publish the limitations, and make remeasurement cheap.

Built by [Duncan Anderson](https://www.duncananderson.ca/), a technical researcher and product/data engineer working across APIs, AI workflows, and production reliability.

## License

MIT. Endpoint data remains subject to each provider's terms; this repository does not license or redistribute their content.
