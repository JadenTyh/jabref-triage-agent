"""
Measure an issue-triage baseline for a GitHub repo.

Usage:
    python3 scripts/baseline.py --repo JabRef/jabref --days 90
    python3 scripts/baseline.py --repo JabRef/jabref --days 90 --triage-label "status: needs-triage"
"""
import argparse, json, re, statistics, subprocess, sys
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from urllib.parse import quote
from nltk.corpus import stopwords

MAINTAINER_ROLES = {"OWNER", "MEMBER", "COLLABORATOR"}
# STOPWORDS = {"the", "a", "an", "in", "on", "of", "to", "for", "and", "or", "is", "are",
#              "not", "with", "when", "after", "from", "at", "by", "it", "as", "be", "this"}
STOPWORDS = set(stopwords.words("english"))

# Call `github api <endpoint>` and return parsed JSON. Stops with a clear error if it fails.
def github_api(endpoint):
    result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"github api failed for {endpoint}\n{result.stderr.strip()}")
    return json.loads(result.stdout)

# Return (total_count, items). The Search API caps at 1000 results (10 pages of 100).
def search_issues(query, max_pages=10):
    items, total = [], 0
    for page in range(1, max_pages + 1):
        data = github_api(f"search/issues?q={quote(query)}&per_page=100&page={page}")
        total = data["total_count"]
        items += data["items"]
        if len(data["items"]) < 100:
            break
    return total, items

def count_only(query): # Counts issues matching a query without fetching them all.
    return github_api(f"search/issues?q={quote(query)}&per_page=1")["total_count"]

def ts(s): # Convert GitHub timestamp string to datetime (aware, UTC).
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

# Hours until the first non-author, non-bot comment (any_resp) and first maintainer one.
def first_responses(repo, issue):
    author = (issue.get("user") or {}).get("login")
    created = ts(issue["created_at"])
    any_resp = maint_resp = None
    for c in github_api(f"repos/{repo}/issues/{issue['number']}/comments?per_page=100"):
        user = c.get("user") or {}
        login = user.get("login", "")
        if login == author or user.get("type") == "Bot" or login.endswith("[bot]"):
            continue
        hours = (ts(c["created_at"]) - created).total_seconds() / 3600
        if any_resp is None:
            any_resp = hours
        if maint_resp is None and c.get("author_association") in MAINTAINER_ROLES:
            maint_resp = hours
        if any_resp is not None and maint_resp is not None:
            break
    return any_resp, maint_resp

def pct(values, p): # p-th percentile of a list of numbers
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]

def tokens(title): # r
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}

# Cheap proxy: open issues whose titles share >= threshold of their words (Jaccard).
def candidate_duplicate_pairs(issues, threshold=0.6):
    toks = [(i["number"], tokens(i["title"])) for i in issues]
    pairs = []
    for (n1, t1), (n2, t2) in combinations(toks, 2):
        if len(t1) < 3 or len(t2) < 3:
            continue
        score = len(t1 & t2) / len(t1 | t2)
        if score >= threshold:
            pairs.append({"a": n1, "b": n2, "jaccard": round(score, 2)})
    return sorted(pairs, key=lambda p: -p["jaccard"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name, e.g. JabRef/jabref")
    ap.add_argument("--days", type=int, default=90, help="look-back window for new issues")
    ap.add_argument("--triage-label", default="status: needs-triage")
    ap.add_argument("--out", default="evals/baseline")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=args.days)).date().isoformat()
    repo = args.repo

    # 1) Backlog right now
    open_total, open_issues = search_issues(f"repo:{repo} is:issue is:open")
    triage_open = count_only(f'repo:{repo} is:issue is:open label:"{args.triage_label}"')
    ages = [(now - ts(i["created_at"])).days for i in open_issues]

    # 2) Issues opened inside the window
    win_total, window = search_issues(f"repo:{repo} is:issue created:>={start}")
    closed_dupes = [i for i in window if i.get("state_reason") == "duplicate"
                    or any("duplicate" in l["name"].lower() for l in i.get("labels", []))]
    dup_comment_hits = count_only(f'repo:{repo} is:issue created:>={start} "duplicate of" in:comments')

    # 3) Time to first response (only issues old enough to have had 7 days to be answered)
    mature = [i for i in window if (now - ts(i["created_at"])).days >= 7]
    any_hours, maint_hours, unanswered_7d, unanswered_maint_7d = [], [], 0, 0
    for issue in mature:
        any_h, maint_h = first_responses(repo, issue)
        if any_h is not None:
            any_hours.append(any_h)
        if maint_h is not None:
            maint_hours.append(maint_h)
        if any_h is None or any_h > 7 * 24:
            unanswered_7d += 1
        if maint_h is None or maint_h > 7 * 24:
            unanswered_maint_7d += 1

    pairs = candidate_duplicate_pairs(open_issues)

    result = {
        "repo": repo,
        "generated_at": now.isoformat(timespec="seconds"),
        "window": {"from": start, "to": now.date().isoformat(), "days": args.days},
        "backlog": {
            "open_issues": open_total,
            "open_needing_triage_label": triage_open,
            "median_open_age_days": statistics.median(ages) if ages else None,
            "open_older_than_365d": sum(1 for a in ages if a > 365),
            "open_issues_fetched": len(open_issues),
        },
        "new_issues": {
            "created_in_window": win_total,
            "old_enough_for_response_metric": len(mature),
        },
        "first_response_hours": {
            "any_human_non_author": {
                "answered": len(any_hours),
                "median": round(statistics.median(any_hours), 1) if any_hours else None,
                "p90": round(pct(any_hours, 90), 1) if any_hours else None,
                "no_response_within_7d": unanswered_7d,
            },
            "maintainer_role": {
                "answered": len(maint_hours),
                "median": round(statistics.median(maint_hours), 1) if maint_hours else None,
                "p90": round(pct(maint_hours, 90), 1) if maint_hours else None,
                "no_response_within_7d": unanswered_maint_7d,
            },
        },
        "duplicates": {
            "marked_duplicate_in_window": len(closed_dupes),
            "issues_in_window_with_duplicate_of_comment": dup_comment_hits,
            "open_title_similarity_pairs_ge_0.6": len(pairs),
            "top_pairs_to_inspect_by_hand": pairs[:15],
        },
        "limitations": [
            "First response = first comment by a non-author, non-bot account; labels/reactions/edits are ignored.",
            "Median/p90 use answered issues only (survivorship bias): read the 'no response within 7d' counts too.",
            "Maintainer role = GitHub author_association OWNER/MEMBER/COLLABORATOR; may miss maintainers with hidden membership.",
            "Duplicates are only counted if someone marked them (state_reason/label) or wrote 'duplicate of'; unmarked duplicates are invisible.",
            "Title-similarity pairs are a rough proxy; inspect the pairs by hand to estimate precision.",
            "Search API returns at most 1000 results, so very large windows/backlogs are truncated.",
        ],
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"baseline-{repo.replace('/', '-')}-{now.date().isoformat()}.json"
    out_file.write_text(json.dumps(result, indent=2) + "\n")

    fr = result["first_response_hours"]["any_human_non_author"]
    fm = result["first_response_hours"]["maintainer_role"]
    print(f"## Baseline for {repo} ({start} to {now.date()}, {args.days} days)\n")
    print(f"- Open issues now: {open_total} ({triage_open} still labelled '{args.triage_label}')")
    print(f"- Median age of open issues: {result['backlog']['median_open_age_days']} days; "
          f"{result['backlog']['open_older_than_365d']} older than a year")
    print(f"- New issues in window: {win_total} ({len(mature)} at least 7 days old)")
    print(f"- First human reply: median {fr['median']} h, p90 {fr['p90']} h, "
          f"{fr['no_response_within_7d']}/{len(mature)} had none within 7 days")
    print(f"- First maintainer reply: median {fm['median']} h, p90 {fm['p90']} h, "
          f"{fm['no_response_within_7d']}/{len(mature)} had none within 7 days")
    print(f"- Marked duplicate in window: {len(closed_dupes)}; "
          f"'duplicate of' comments: {dup_comment_hits}; similar open-title pairs: {len(pairs)}")
    print(f"\nSaved raw numbers to {out_file}")


if __name__ == "__main__":
    main()