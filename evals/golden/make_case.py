#!/usr/bin/env python3
"""
make_case.py - scaffold one golden case from a real JabRef issue.

Usage (from the repo root):
  python3 evals/golden/make_case.py --number 17379 --slug tooltip-shadow --category "clear GUI bug"

Creates evals/golden/cases/NN-slug/ with:
  input.json         what will be replayed to the agent (title + body only are used)
  ground_truth.json  what happened later in reality (hindsight, NEVER shown to the agent)
  expected.json      what the agent SHOULD do - you fill this in BEFORE running the agent
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

CASES = Path(__file__).resolve().parent / "cases"

def gh_api(endpoint):
    result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"gh api failed for {endpoint}\n{result.stderr.strip()}")
    return json.loads(result.stdout)

def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="JabRef/jabref")
    ap.add_argument("--number", type=int, required=True)
    ap.add_argument("--slug", required=True, help="short name, e.g. tooltip-shadow")
    ap.add_argument("--category", default="TODO")
    args = ap.parse_args()

    issue = gh_api(f"repos/{args.repo}/issues/{args.number}")
    if "pull_request" in issue:
        sys.exit(f"#{args.number} is a pull request, not an issue.")

    CASES.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]+", "-", args.slug.lower()).strip("-")
    if any(p.name.endswith("-" + slug) for p in CASES.iterdir()):
        sys.exit(f"A case with slug '{slug}' already exists.")
    case_id = f"{len([p for p in CASES.iterdir() if p.is_dir()]) + 1:02d}-{slug}"
    case_dir = CASES / case_id
    case_dir.mkdir()

    write(case_dir / "input.json", {
        "title": issue["title"],
        "body": issue.get("body") or "",
        "source": {
            "repo": args.repo,
            "original_number": issue["number"],
            "original_url": issue["html_url"],
            "created_at": issue["created_at"],
            "note": "Only title and body are replayed. Body is the CURRENT text and may have been edited after creation.",
        },
    })
    write(case_dir / "ground_truth.json", {
        "WARNING": "Hindsight only. Never shown to the agent. Use it to decide expected.json.",
        "labels_today": [label["name"] for label in issue.get("labels", [])],
        "state": issue["state"],
        "state_reason": issue.get("state_reason"),
        "closed_at": issue.get("closed_at"),
        "comment_count": issue.get("comments"),
    })
    write(case_dir / "expected.json", {
        "case_id": case_id,
        "category": args.category,
        "comment": "TODO: expected | none",
        "labels_must_include": [],
        "labels_allowed_extra": [],
        "labels_forbidden": [],
        "max_labels": 3,
        "comment_must_link": [],
        "must_not_close_anything": True,
        "rationale": "TODO: why this is the right outcome (write it BEFORE running the agent)",
    })
    print(f"Created {case_dir}\nNext: edit {case_dir / 'expected.json'} and replace every TODO.")

if __name__ == "__main__":
    main()