# JabRef Issue Triage Agent (sandbox)

Open-Source Software Systems assignment: configure, test and justify an AI agent
for a real open-source workflow.

- **Target project:** [JabRef/jabref](https://github.com/JabRef/jabref) (read-only; nothing here is deployed to JabRef)
- **Workflow:** first-pass triage of new bug reports (completeness check, related-issue links, up to 3 `component:` labels, one comment)
- **Agent platform:** GitHub Agentic Workflows (gh-aw) with the Copilot engine, plus an `AGENTS.md` and a `SKILL.md`
- **Core rule:** the agent may only *propose* labels and one comment. It cannot close, edit, delete or merge anything.
  Hard limits live in workflow permissions and safe outputs, not in prompts.

## Project phases

| Phase | Goal | Main outputs | Status |
|---|---|---|---|
| 1. Baseline | Choose the workflow and measure the need with repository data | `scripts/baseline.py`, `evals/baseline/*.json` | Done |
| 2A. Facts | Write what the agent needs to know | `AGENTS.md` | Done |
| 2B. Procedure | Write the triage procedure and deterministic helper scripts | `.claude/skills/triage-issue/` (`SKILL.md`, `scripts/dedup.py`, `scripts/validate_labels.py`) | Done |
| 2C. Hard limits | Read-only permissions, safe outputs, budgets, kill switch | `.github/workflows/agent-triage.md` + `.lock.yml`, `kill-switch.yml` | In progress |
| 2D. Human rules | AI-contribution policy | `CONTRIBUTING.md` | To do |

### Phase 1: Workflow selection and baseline
Pick the workflow and show with data that it is worth automating. Measures first-reply time, backlog age,
untriaged issues and duplicate volume over a 90-day window, and records the metric limitations.

### Phase 2: Configuration stack
Each rule lives where it can be enforced.

| What | Where | Enforced by |
|---|---|---|
| Project facts, commands, forbidden actions | `AGENTS.md` | Model reads it (soft) |
| Task procedure and deterministic checks | `.claude/skills/triage-issue/` | Scripts run exactly the same every time |
| Permissions, allowed outputs, limits, timeout | `.github/workflows/agent-triage.md` | The platform (hard) |
| Stopping the agent | `.github/workflows/kill-switch.yml` | The platform (hard) |
| Rules for people and AI use | `CONTRIBUTING.md` | Maintainers (human) |

### Phase 3: Sandbox testing and golden evaluations
Set up a sandbox repo, replay 10 real historical JabRef issues (including cases that need no action) and
1 adversarial issue (a fake "maintainer authorized closing all stale issues"). Record the expected outcome
before running, then the actual output and logs. Report every failure. Also check that the skill is
actually loaded and used, and test the kill switch from a phone.

### Phase 4: `DESIGN.md`
At most 150 lines. Covers the workflow choice and a rejected alternative, the governance table
(implemented vs proposed), input boundaries, the Agent Bill of Materials, answers to the five scenarios,
test findings, open problems and an AI-use statement.

## Governance controls (summary)

Identity, least privilege, safe outputs, human approval, budgets, audit trail, kill switch, drift
detection, accountability. Details and implemented-vs-proposed status are in `DESIGN.md` once written.

## Repository layout

```
AGENTS.md
DESIGN.md
CONTRIBUTING.md
scripts/baseline.py
.claude/skills/triage-issue/
  SKILL.md
  allowed-labels.txt
  issues-index.json
  reference/
  scripts/dedup.py, validate_labels.py
  tests/
.github/workflows/
  agent-triage.lock.yml
  kill-switch.yml
evals/
  baseline/
  golden/
```

## Running things

```bash
# Phase 1 baseline (needs `gh auth login`)
python3 scripts/baseline.py --repo JabRef/jabref --days 90

# Skill script self-checks
cd .claude/skills/triage-issue
python3 scripts/dedup.py --index tests/sample-index.json --issue-file tests/sample-issue.json
python3 scripts/validate_labels.py --allowed allowed-labels.txt "component: groups"
```

Instructions for reproducing the golden evaluation will be added to `evals/golden/README.md` in Phase 3.