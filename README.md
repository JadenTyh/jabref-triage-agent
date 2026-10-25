# jabref-triage-agent

## Commands to run before getting started
- `pip install -r requirements.txt`

## Phase 1: Baseline script & JabRef issue metrics
- run `python3 scripts/baseline.py --repo JabRef/jabref --days 90`
- Makes a few run 100 read-only requests to GitHub