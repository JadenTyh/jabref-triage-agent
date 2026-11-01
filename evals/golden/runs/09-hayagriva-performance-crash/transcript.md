# Triage transcript: JabRef/jabref#17620

**Issue:** Hayagriva YAML export crashes on `@performance` entries: `No enum constant StandardEntryType.Performance`
**Task:** Follow `.claude/skills/triage-issue/SKILL.md`. Dry-run: finish with one JSON block.

## Commands

| # | Tool  | Target |
|---|-------|--------|
| 1 | Read  | `.claude/skills/triage-issue/SKILL.md` |
| 2 | Read  | `.claude/skills/triage-issue/allowed-labels.txt` |
| 3 | Write | `/tmp/issue.json` |
| 4 | Bash  | `dedup.py` and `validate_labels.py` (one call) |
| 5 | Read  | `.claude/skills/triage-issue/reference/comment-template.md` |

`AGENTS.md` was not read with a tool call. Its contents were already in context at session start.
The completeness checklist was not opened: the body has version, OS, steps, a stack trace and expected behaviour.

### 3. Write issue.json

```json
{"title": "Hayagriva YAML export crashes on `@performance` entries: `No enum constant StandardEntryType.Performance`", "body": "Exporting a library to Hayagriva YAML fails whenever the library contains a @performance entry, and the whole export aborts. The exporter maps the entry type through StandardEntryType.valueOf(\"Performance\"), but that enum has no Performance constant. IllegalArgumentException at HayagrivaType.format, TemplateExporter.export."}
```

### 4. Dedup and label validation

```bash
python3 .claude/skills/triage-issue/scripts/dedup.py \
  --index .claude/skills/triage-issue/issues-index.json \
  --issue-file /tmp/issue.json --top 3

python3 .claude/skills/triage-issue/scripts/validate_labels.py \
  --allowed .claude/skills/triage-issue/allowed-labels.txt \
  "component: export-or-save" "component: bib(la)tex"
```

**Output**

```json
{
  "checked": 1001,
  "candidates": []
}
{
  "ok": ["component: export-or-save", "component: bib(la)tex"],
  "rejected": [],
  "dropped_over_limit": []
}
```

## Reasoning summary

- Classified as a bug report and complete, so no missing-information request.
- `dedup.py` returned no candidates. #10382 and #10596 appear only in the issue text, which the reporter says are not the same bug, so they are not listed as related.
- One label, `component: export-or-save`, because the failure is in the export layout code. `component: bib(la)tex` validated but was dropped to keep the proposal minimal.
- No comment: none of rules (a), (b) or (c) applies, and a comment that only lists labels is not allowed.

## Final output

```json
{"labels": ["component: export-or-save"], "comment": null}
```
