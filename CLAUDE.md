# shape_of_tax_system_2026_FR

A sunburst chart of the French tax system (2023 data), built as a fork of DanNeidle's UK tax system chart. The French build is `build_fr_tax_system_chart.py`; it writes `fr_tax_system_sunburst_2023.json` and is run by Vercel via `vercel.json`.

## Review process

- **Checks** (run before every PR and paste the real output; never claim they pass without running them): `python3 build_fr_tax_system_chart.py` (the Vercel build command from `vercel.json`; it prints a total per view, which should be compared with the published totals). No test suite, linter or CI workflow exists yet.
- **Before a PR**: fresh-context subagent review of the diff + `/code-review` + `/security-review`. See `REVIEW.md` for what reviewers must check in this repo.
- **PR body** must have **Testing**, **Risk** (Low/Medium/High + why) and **How to revert** (`.github/pull_request_template.md`).
- **Risk is set by the change, not the author.** High (never auto-merged): auth, secrets, CI/deploy config, economic parameters or calculations, anything hard to undo.
- **Findings**: label Important / Nit / Pre-existing; fix each or resolve it with a written reason. Max 3 review-and-fix rounds, then rethink the approach.
- Patrick is the required human reviewer on every agent-written PR. One concern per PR.
- **Fork:** this repo is a fork of DanNeidle/shape_of_tax_system_2026. Every `gh pr create` must include `--repo alles-delenda-est/shape_of_tax_system_2026_FR`; never open PRs or issues on the upstream repo.
