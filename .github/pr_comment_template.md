<!--DECISIONOS:PR:RELEASE_GATE-->
### 🚦 Release Gates: **{{STATUS_EMOJI}} {{STATUS}}**

**Infra Gate:** `{{INFRA_STATUS}}` &nbsp;|&nbsp; **Canary Gate:** `{{CANARY_STATUS}}`
**Run:** {{RUN_URL}}

#### Top Reasons (code → message)
| code | message | count |
|------|---------|------:|
{{REASONS_ROWS}}

#### Artifacts
- Evidence: [latest.json]({{EVIDENCE_URL}})
- Gate Report: [report.json]({{REPORT_URL}})
- Ops Cards: [reason-trends]({{OPS_TRENDS_URL}}) · [top-impact]({{OPS_IMPACT_URL}})

> inspector: {{INSPECTOR}} · generated: {{GENERATED_AT}}
