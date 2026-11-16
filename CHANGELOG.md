# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- `--dry-run` on `cc_full_experiment.py` uses a deterministic offline mock LLM
  and does not call the network. Live runs are unchanged.
- `identifiability.py` and `make check` recompute a synthetic identifiability
  study (temporal drift vs peer contagion vs a null) with the repo's own
  Wilcoxon reading. The README fractions are that study, not manuscript results.
- LICENSE-DATA no longer says a CC BY 4.0 dataset is in the tree. No result
  files were added.
- Governance baseline: LICENSE, security policy, code of conduct, contributor and
  support guides, issue and pull-request templates, CODEOWNERS, dependabot, and
  `.editorconfig` added. No research content changed.
