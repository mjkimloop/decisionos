# Release Gate PR Visibility

## Overview

After the `post_gate` job succeeds, CI performs the following actions:

1. **Artifact validation** — `scripts.ci.validate_artifacts` checks the evidence JSONs (index/gc/upload/dr) for existence and minimum fields. Failure stops visibility updates.
2. **Checks API update** — `scripts.ci.github_checks` submits a GitHub Check Run summarizing pre/gate/post status with a link back to the workflow run.
3. **PR comment upsert** — `scripts.ci.annotate_release_gate` renders badges, artifact summaries, reasons/top-impact tables, GameDay/DR results and posts/updates a single comment marked by `DECISIONOS_COMMENT_MARKER`.
4. **Label sync (optional)** — When reasons include label codes from `configs/labels/label_catalog_v2.json`, the script ensures the labels exist in the repo and attaches them to the PR.
5. **Change Governance 배지** — `var/ci/change_status.json`에 Freeze / CAB / Oncall 결과를 저장하고 PR 코멘트 및 Checks 섹션에 표시한다.

All actions honour `DECISIONOS_VISIBILITY_ENABLE`. When disabled or when `GITHUB_TOKEN`/PR context is missing the scripts exit gracefully without failing CI.
