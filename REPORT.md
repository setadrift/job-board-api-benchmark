# Public job-board API benchmark

Measured at **2026-08-24T18:21:54+00:00** using 3 sequential requests per list endpoint.

| ATS and test board | Records | Median latency (ms) | Location present | Published date present | Candidate URL in list | Duplicate IDs | Sampled links reachable |
|---|---:|---:|---:|---:|---:|---:|---:|
| Greenhouse (GitLab) | 204 | 517.8 | 100% | 100% | 100% | 0 | 100% |
| Ashby (SearchApi) | 12 | 239.2 | 100% | 100% | 100% | 0 | 100% |
| Lever (Palantir) | 308 | 1461.4 | 100% | 100% | 100% | 0 | 100% |
| SmartRecruiters (ServiceNow) | 100 | 641.9 | 100% | 100% | 0% | 0 | n/a |

## What this result means

This is a comparison of four **specific public job-board list endpoints**, not a universal ranking of the ATS products. The company boards differ in size and geography, network conditions vary, and SmartRecruiters intentionally requires a detail request before returning a candidate-facing URL; its list-response score should not be read as a product defect.

## Reproduce it

```bash
python benchmark.py --runs 3 --link-sample 3
```

The command rewrites `results/latest.json`, appends a dated history snapshot, and regenerates this report. Raw third-party job descriptions are not republished; each result stores normalized aggregates plus a SHA-256 digest of the received payload.

## Method and limitations

- Requests run sequentially from one machine with the same timeout and user agent.
- Median latency is descriptive, not a controlled infrastructure benchmark.
- Field presence measures the list response only; it does not judge fields available through detail endpoints.
- Candidate-link checks sample the first available URLs and treat HTTP 200-399 as reachable.
- Public endpoints can change or rate-limit without notice. Re-measure before relying on the values.
