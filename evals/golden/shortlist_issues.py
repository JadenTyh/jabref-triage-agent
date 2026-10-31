#!/usr/bin/env python3
"""
suggest candidate JabRef issues for each golden-case slot.

Usage (from the repo root):
  python3 evals/golden/shortlist.py [--since 2026-07-27] [--per-slot 4]

Reads recent issues with `gh`, compares them with your offline index, and prints a few
candidates per slot. These are SUGGESTIONS: open each one and check it before using it.
Hindsight data (labels, closed reason) is used only to find candidates, never given to the agent.
"""
import argparse, importlib.util, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude" / "skills" / "triage-issue"
FIELDS = "number,title,body,labels,state,stateReason,comments,createdAt,url"

def gh_issues(repo, since):
    cmd = ["gh", "issue", "list", "-R", repo, "--state", "all", "--limit", "300",
           "--search", f"created:>={since}", "--json", FIELDS]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"gh failed:\n{result.stderr.strip()}")
    return json.loads(result.stdout)

def load_dedup():
    spec = importlib.util.spec_from_file_location("dedup", SKILL / "scripts" / "dedup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def labels(issue):
    return [label["name"] for label in issue.get("labels", [])]

def components(issue):
    return [name for name in labels(issue) if name.startswith("component: ")]

def body(issue):
    return issue.get("body") or ""

def dup_original(issue):
    for comment in issue.get("comments", []):
        match = re.search(r"duplicate of\s+(?:https://github.com/\S+/issues/|#)(\d+)",
                          comment.get("body") or "", re.I)
        if match:
            return int(match.group(1))
    return None

def non_ascii_ratio(text):
    return sum(ord(c) > 127 for c in text) / len(text) if text else 0.0

def complete_bug(issue):
    text = body(issue)
    return ("Steps to reproduce" in text and "1. ..." not in text
            and 300 <= len(text) <= 4000 and issue["state"] is not None)

def show(title, rows, per_slot):
    print(f"\n=== {title}")
    if not rows:
        print("  (no candidates found - try the manual search commands)")
    for row in rows[:per_slot]:
        print("  " + row)

def line(issue, extra=""):
    return f"#{issue['number']} | {issue['title'][:70]} | {extra}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="JabRef/jabref")
    ap.add_argument("--since", default="2026-07-27")
    ap.add_argument("--per-slot", type=int, default=4)
    args = ap.parse_args()

    issues = [i for i in gh_issues(args.repo, args.since) if i.get("createdAt", "")[:10] >= args.since]
    index = json.loads((SKILL / "issues-index.json").read_text(encoding="utf-8"))
    index_numbers = {i["number"] for i in index}
    print(f"{len(issues)} issues created on/after {args.since}; index has {len(index)} older issues.")

    dedup = load_dedup()
    docs = [dedup.doc_text(i.get("title") or "", i.get("body")) for i in index]
    docs += [dedup.doc_text(i["title"], body(i)) for i in issues]
    vectors = dedup.tfidf_vectors(docs)
    index_vectors = vectors[:len(index)]
    best = {}
    for issue, vec in zip(issues, vectors[len(index):]):
        scored = [(sum(w * iv.get(t, 0.0) for t, w in vec.items()), idx)
                  for idx, iv in enumerate(index_vectors)]
        score, idx = max(scored) if scored else (0.0, 0)
        best[issue["number"]] = (score, index[idx] if index else None)

    groups = {
        "Slot 1: clear GUI bug (groups/entry-editor/ui/maintable/preferences...)":
            lambda i: complete_bug(i) and any(c in components(i) for c in (
                "component: groups", "component: entry-editor", "component: ui", "component: maintable",
                "component: preferences", "component: theming", "component: pdf-viewer")),
        "Slot 2: clear core-library bug (fetcher/import/export/bib...)":
            lambda i: complete_bug(i) and any(c in components(i) for c in (
                "component: fetcher", "component: import-load", "component: export-or-save",
                "component: bib(la)tex", "component: citationkey-generator")),
        "Slot 3: command-line tool bug (jabkit)":
            lambda i: "component: jabkit" in components(i),
        "Slot 9: spans several components (2+ component labels)":
            lambda i: len(components(i)) >= 2,
    }
    for title, test in groups.items():
        show(title, [line(i, ", ".join(components(i))) for i in issues if test(i)], args.per_slot)

    show("Slot 4: missing information (placeholder steps or no version)",
         [line(i, "steps placeholder" if "1. ..." in body(i) else "no version field")
          for i in issues if "1. ..." in body(i) or ("JabRef version" not in body(i) and len(body(i)) > 150)],
         args.per_slot)

    dups = []
    for issue in issues:
        original = dup_original(issue)
        if original is None and issue.get("stateReason") == "duplicate":
            continue
        if original is not None:
            dups.append(line(issue, f"duplicate of #{original}; in index: {original in index_numbers}"))
    show("Slot 5: true duplicate (needs 'in index: True')", dups, args.per_slot)

    lookalikes = [line(i, f"score {s:.2f} vs older #{m['number']} '{m['title'][:40]}'")
                  for i in issues for s, m in [best[i["number"]]]
                  if m and 0.30 <= s < 0.7 and dup_original(i) is None and i.get("stateReason") != "duplicate"]
    show("Slot 6: look-alike - READ BOTH and confirm they are DIFFERENT problems", lookalikes, args.per_slot)

    show("Slot 7: feature request or question (by label)",
         [line(i, ", ".join(labels(i))) for i in issues
          if any(k in n.lower() for n in labels(i) for k in ("feature", "enhancement", "question"))],
         args.per_slot)
    show("Slot 8: empty / very short / closed as not planned",
         [line(i, f"{len(body(i))} chars, {i.get('stateReason')}") for i in issues
          if len(body(i)) < 150 or i.get("stateReason") == "not_planned"], args.per_slot)
    show("Slot 10: very long body or mostly non-English",
         [line(i, f"{len(body(i))} chars, non-ascii {non_ascii_ratio(body(i)):.0%}") for i in issues
          if len(body(i)) > 6000 or non_ascii_ratio(body(i)) > 0.3], args.per_slot)

if __name__ == "__main__":
    main()