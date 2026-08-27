# Contributing to SAEPS

Use a branch and pull request for changes. Install the locked environment, run `pytest -q`, and run both repository validators before requesting review.

Scientific evidence files must never be edited by hand. New experiments must use new provenance-bearing output paths and must be clearly separated from existing frozen evidence, registered seeds, failed records, and adjudications. Generated evidence must retain source hashes, configurations, environment metadata, planned denominators, and failure states.

Ordinary code/documentation changes may use the repository's normal merge settings. Branches containing manuscript-facing evidence provenance must be merged with a merge commit; do not squash or rebase those histories.

Do not commit credentials, private data, virtual environments, caches, or local validation outputs.

