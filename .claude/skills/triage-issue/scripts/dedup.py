#!/usr/bin/env python3
"""
dedup.py - list existing issues that look like a new issue. Deterministic: no AI, no network.

Usage:
  python3 dedup.py --index issues-index.json --issue-file new-issue.json [--top 3]
                   [--min-score 0.25] [--before 2026-01-01] [--exclude-number 123]

new-issue.json   : {"title": "...", "body": "..."}
issues-index.json: gh issue list -R JabRef/jabref --state all --limit 1000 \
                   --json number,title,body,createdAt,state
"""
import argparse, json, math, re
from collections import Counter

# Fixed list on purpose: no outside packages exist on the GitHub runner.
stop_words = {"about", "above", "after", "again", "against", "all", "also", "and", "any", "are", "because", "been", "before", "being", "below", "between", "both", "but", "can", "could", "did", "does", "doing", "don", "down", "during", "each", "few", "for", "from", "further", "has", "have", "having", "her", "here", "herself", "him", "himself", "his", "how", "into", "its", "itself", "jabref", "just", "more", "most", "myself", "nor", "not", "now", "off", "once", "only", "other", "our", "ourselves", "out", "over", "own", "response", "same", "she", "should", "some", "such", "than", "that", "the", "their", "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "too", "under", "until", "very", "was", "were", "what", "when", "which", "while", "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself"}

def clean_body(body):
    """Drop form headings and checkbox lines, which are identical in every bug report."""
    lines = [ln for ln in (body or "").splitlines()
             if not ln.lstrip().startswith(("###", "- [", "* ["))]
    return "\n".join(lines)

def tokenize(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in stop_words]

def doc_text(title, body):
    return (title + " ") * 3 + clean_body(body)[:2000]  # the title counts triple

def tfidf_vectors(docs):
    token_lists = [tokenize(d) for d in docs]
    df = Counter()
    for toks in token_lists:
        df.update(set(toks))
    n = len(docs)
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
    vectors = []
    for toks in token_lists:
        weights = {t: (1 + math.log(c)) * idf[t] for t, c in Counter(toks).items()}
        norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
        vectors.append({t: w / norm for t, w in weights.items()})
    return vectors

def main():
    ap = argparse.ArgumentParser(description="Find possibly related issues (deterministic).")
    ap.add_argument("--index", required=True)
    ap.add_argument("--issue-file", required=True)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--min-score", type=float, default=0.25)
    ap.add_argument("--before", help="only compare with issues created before YYYY-MM-DD")
    ap.add_argument("--exclude-number", type=int, help="skip this issue number")
    ap.add_argument("--repo-url", default="https://github.com/JabRef/jabref")
    args = ap.parse_args()

    with open(args.index, encoding="utf-8") as f:
        index = json.load(f)
    with open(args.issue_file, encoding="utf-8") as f:
        new_issue = json.load(f)

    pool = [i for i in index
            if i.get("number") != args.exclude_number
            and (not args.before or (i.get("createdAt") or "")[:10] < args.before)]
    docs = [doc_text(i.get("title") or "", i.get("body")) for i in pool]
    docs.append(doc_text(new_issue.get("title") or "", new_issue.get("body")))
    vectors = tfidf_vectors(docs)
    query = vectors[-1]

    scored = []
    for item, vec in zip(pool, vectors[:-1]):
        score = sum(w * vec.get(t, 0.0) for t, w in query.items())
        if score >= args.min_score:
            scored.append({"number": item["number"], "title": item.get("title"),
                           "state": item.get("state"),
                           "url": f"{args.repo_url}/issues/{item['number']}",
                           "score": round(score, 2)})
    scored.sort(key=lambda c: -c["score"])
    print(json.dumps({"checked": len(pool), "candidates": scored[: args.top]}, indent=2))

if __name__ == "__main__":
    main()