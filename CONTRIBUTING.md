# Contributing

## AI use in this repository

### The triage bot
- On every new issue, an AI agent may add up to 3 `component:` labels and post one comment.
- Its comment starts with "🤖 Automated first-pass triage (AI-generated, not yet reviewed by a maintainer)".
- It cannot close, edit, delete or assign issues, and it cannot touch code or pull requests.
- A maintainer makes every real decision. If the bot is wrong, correct the labels and carry on.

### Humans using AI tools
- You are responsible for everything you submit. You must understand every change and be able to explain it.
- Disclose any AI tool you used, with the exact model ID, in the pull request or issue description.
- Do not paste unreviewed AI output as a reply to a reviewer or maintainer.
- Text you write in issues may be read by the triage bot. Do not include instructions aimed at AI tools.

### Maintainers
- To stop the bot immediately: Actions → "Kill switch" → Run workflow → `stop`.
- Only maintainers may change `AGENTS.md`, `.claude/`, or `.github/workflows/`.
  Such changes need a pull request and a review.