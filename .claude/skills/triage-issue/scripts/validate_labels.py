"""
validate_labels.py - check proposed labels against the allowlist. Deterministic: no AI.

Usage:
  python3 validate_labels.py --allowed allowed-labels.txt "component: groups" "component: ui"
Exit code 0 = all labels fine, 1 = something was rejected or there were more than 3.
"""

import argparse, json, sys

MAX_LABELS = 3

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowed", required=True)
    ap.add_argument("labels", nargs="*")
    args = ap.parse_args()

    with open(args.allowed, encoding="utf-8") as f:
        allowed = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}

    seen = []
    for label in args.labels:
        if label not in seen:
            seen.append(label)
    ok = [label for label in seen if label in allowed]
    rejected = [label for label in seen if label not in allowed]

    print(json.dumps({"ok": ok[:MAX_LABELS], "rejected": rejected,
                      "dropped_over_limit": ok[MAX_LABELS:]}, indent=2))
    sys.exit(1 if rejected or len(ok) > MAX_LABELS else 0)

if __name__ == "__main__":
    main()