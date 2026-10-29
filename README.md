# jabref-triage-agent

## Commands to run before getting started
- `pip install -r requirements.txt`

## Phase 1: Baseline script & JabRef issue metrics
- run `python3 scripts/baseline.py --repo JabRef/jabref --days 90`
- Makes a few run 100 read-only requests to GitHub

## Phase 2
Where Phase 2 stands

Phase 2 has four steps. This message covers the first two, which set up what the agent knows and how it works. The next message covers the last two, which set up what the agent is allowed to do.

Step	File	Job
2A	AGENTS.md	Facts about the project and the forbidden actions
2B	.claude/skills/triage-issue/…	The triage procedure plus two deterministic scripts
2C (next)	.github/workflows/agent-triage.md	Hard limits the model can’t bypass
2D (next)	CONTRIBUTING.md	Human rules for AI use

### Commands to run 
- wc -l AGENTS.md
    - Should be 63 lines

- SKILL.md