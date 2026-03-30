# QuickBooks Version Tracker

Automatically tracks the latest QuickBooks desktop installer versions (US Windows, 2022–2024) by checking Intuit's download servers twice a day.

## How it works

- A GitHub Actions workflow (`check-versions.yml`) runs `check_versions.py` twice daily at midnight and noon UTC (or on demand via `workflow_dispatch`).
- The script sends HTTP HEAD requests to the official Intuit download URLs and records the `Last-Modified` date and file size for each product.
- Results are written to `versions.json` and committed back to the repository.

## Files

| File | Description |
|------|-------------|
| `check_versions.py` | Python script that checks QB download URLs and writes `versions.json` |
| `.github/workflows/check-versions.yml` | GitHub Actions workflow that runs the script on a schedule |
| `versions.json` | Latest recorded version data (auto-updated by the workflow) |

## Products tracked

- QuickBooks Pro 2022–2024
- QuickBooks Premier 2022–2024
- QuickBooks Accountant 2022–2024
- QuickBooks Enterprise 22–24 (standard and accountant editions)
