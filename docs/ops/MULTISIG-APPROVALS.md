# Multisig Approval Requirements

**Owner**: Platform Security
**Updated**: 2025-11-16
**Version**: v0.5.11v

---

## Overview

Critical policy changes require **multiple approvers** (multisig) to prevent single-point-of-failure in the approval process.

This provides:
- **Defense in depth**: No single person can push malicious policy changes
- **Separation of duties**: Different teams review changes affecting their domain
- **Audit trail**: All approvals are recorded in PR history
- **Compliance**: Meets regulatory requirements for critical system changes

---

## Approval Rules

### Rule Configuration

Approval rules are defined in [`.github/approval_policies.yaml`](../../.github/approval_policies.yaml).

Each rule specifies:
- `glob`: File pattern to match (supports `{ext1,ext2}` syntax)
- `required_approvers`: Minimum total approvers
- `required_teams`: Teams that must approve (optional)
- `min_per_team`: Minimum approvers per team (default: 1)
- `description`: Human-readable description

### Default Rules

| Policy Type | Glob Pattern | Approvers | Teams | Description |
|-------------|--------------|-----------|-------|-------------|
| **RBAC** | `configs/policy/rbac*.{json,yaml}` | 2 | security | RBAC changes require 2 security team approvals |
| **SLO** | `configs/policy/slo*.json` | 2 | platform | SLO changes require 2 platform team approvals |
| **Canary** | `configs/policy/canary*.{json,yaml}` | 2 | platform, service | Canary changes require 1 platform + 1 service approver |
| **Freeze Windows** | `configs/change/freeze*.yaml` | 2 | platform | Freeze window changes require 2 platform approvals |
| **Ownership** | `configs/change/ownership.yaml` | 2 | platform | Ownership changes require 2 platform approvals |
| **Default** | `configs/policy/*.{json,yaml}` | 2 | (any) | Default 2-approver requirement |
| **Registry** | `configs/policy/registry.json` | 3 | security, platform | Policy registry requires security + platform (3 total) |

---

## CI Integration

### Pre-Gate Check

The multisig check runs automatically in PRs:

```yaml
- name: Check multisig approvals
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    CI_PR_NUMBER: ${{ github.event.pull_request.number }}
    CI_REPO: ${{ github.repository }}
  run: python -m scripts.ci.check_multisig
```

**Exit Codes**:
- `0`: All requirements met or check skipped (no GITHUB_TOKEN)
- `3`: Requirements NOT met (PR blocked)

### Check Behavior

1. **Scan changed files** in PR (`git diff`)
2. **Match against rules** in `approval_policies.yaml`
3. **Fetch PR reviews** from GitHub API
4. **Count approvers** per team (heuristic: username patterns)
5. **Verify requirements** met for all matching rules
6. **Block PR** if requirements not met

### Override Label

**Emergency bypass**: Add label `review/2-approvers` to skip check.

```bash
gh pr edit <PR_NUMBER> --add-label "review/2-approvers"
```

⚠️ **WARNING**: Only use for emergency hotfixes. Requires post-incident review.

---

## Team Membership

### Current Implementation

Team membership is determined **heuristically** by username patterns:

| Team | Username Pattern |
|------|------------------|
| `security` | Contains `sec`, `security` |
| `platform` | Contains `platform`, `infra` |
| `service` | Contains `service`, `svc` |

### Future: GitHub Teams API

Production should use GitHub Teams API:

```python
# GET /orgs/{org}/teams/{team}/memberships/{username}
response = api("GET", f"/orgs/{org}/teams/security/memberships/{username}")
if response.get("state") == "active":
    teams.add("security")
```

**Tracking**: See [Issue #123](#) for GitHub Teams integration

---

## Examples

### Example 1: RBAC Policy Change

**PR**: Change `configs/policy/rbac_map.json`

**Rule**: RBAC policies require 2 security team approvals

**Approval Flow**:
1. `alice-security` reviews and approves ✅
2. `bob-security` reviews and approves ✅
3. Multisig check: **PASSES** ✓

### Example 2: SLO Policy Change

**PR**: Change `configs/policy/slo.json`

**Rule**: SLO policies require 2 platform team approvals

**Approval Flow**:
1. `charlie-platform` reviews and approves ✅
2. `david-security` reviews and approves ❌ (wrong team)
3. Multisig check: **FAILS** ✗

**Fix**: Get approval from another platform team member

### Example 3: Canary Policy Change

**PR**: Change `configs/policy/canary_policy.json`

**Rule**: Canary policies require 1 platform + 1 service approver

**Approval Flow**:
1. `eve-platform` reviews and approves ✅
2. `frank-service` reviews and approves ✅
3. Multisig check: **PASSES** ✓

### Example 4: Multiple Policy Changes

**PR**: Changes both `rbac_map.json` AND `slo.json`

**Rules**:
- RBAC requires 2 security approvers
- SLO requires 2 platform approvers

**Approval Flow**:
1. `alice-security` approves ✅
2. `bob-security` approves ✅
3. `charlie-platform` approves ✅
4. Multisig check: **FAILS** ✗ (only 1 platform approver)

**Fix**: Get one more platform team approval

---

## Manual Verification

### Check PR Approvals

```bash
# View PR reviews
gh pr view <PR_NUMBER> --json reviews

# View approvers
gh pr view <PR_NUMBER> --json reviews \
  --jq '.reviews[] | select(.state=="APPROVED") | .author.login'
```

### Test Multisig Check Locally

```bash
# Set environment variables
export GITHUB_TOKEN="ghp_..."
export CI_PR_NUMBER=123
export CI_REPO="org/DecisionOS"

# Run check
python -m scripts.ci.check_multisig
```

**Output**:
```
PR #123: 2 approvers: alice-security, bob-security

❌ Multisig approval requirements NOT met:

  - SLO and infrastructure policies: requires 2 approvers, got 0

Add required approvals or apply 'review/2-approvers' label to override
```

---

## Customizing Rules

### Add New Rule

Edit [`.github/approval_policies.yaml`](../../.github/approval_policies.yaml):

```yaml
rules:
  - name: Cost optimization policies
    glob: "configs/billing/*.json"
    required_approvers: 3
    required_teams:
      - finance
      - platform
    min_per_team: 1
    description: Billing changes require finance + platform approval
```

### Override with Custom File

Set environment variable:

```bash
export DECISIONOS_POLICY_APPROVERS_YAML="custom-approvals.yaml"
```

### Disable Team Requirements

Remove `required_teams` from rule:

```yaml
rules:
  - name: Generic policy changes
    glob: "configs/policy/*.json"
    required_approvers: 2
    # No team requirements - any 2 approvers
```

---

## Troubleshooting

### Error: "team 'security' requires 2 approvers, got 0"

**Cause**: No security team members have approved the PR.

**Fix**:
1. Request review from security team: `@org/security`
2. Wait for approvals
3. Re-run check

### Warning: "Skipping multisig check: missing GITHUB_TOKEN"

**Cause**: Running in non-PR context (local dev, manual workflow).

**Fix**: This is expected in local environments. In CI, ensure:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Error: "No files changed, skipping multisig check"

**Cause**: PR has no file changes (empty diff).

**Fix**: This is normal for empty PRs. Add file changes or close PR.

### Team membership not recognized

**Cause**: Username doesn't match team patterns (heuristic limitation).

**Workaround**:
1. Add override label: `review/2-approvers`
2. Manually verify approvers in PR comments
3. Track in [Issue #123](#) for GitHub Teams API integration

---

## Security Considerations

### Threat: Single Compromised Account

**Mitigation**: Multisig requires ≥2 approvers, so a single compromised account cannot approve malicious changes alone.

### Threat: Collusion (Multiple Compromised Accounts)

**Mitigation**:
- Team separation: Different teams review changes affecting their domain
- Audit trail: All approvals recorded in Git history
- Post-deployment monitoring: Automated alerts on policy changes

### Threat: Override Label Abuse

**Mitigation**:
- Label events logged in audit trail
- Alerts on `review/2-approvers` label usage
- Post-incident review required for all overrides

### Threat: Team Membership Manipulation

**Current**: Heuristic-based team matching (limited protection)
**Future**: GitHub Teams API with org admin controls

---

## Compliance

### SOC 2

**Control**: Change Management (CC8.1)
**Evidence**: PR approval records in GitHub

### ISO 27001

**Control**: A.12.1.2 Change Management
**Evidence**: Approval policies + Git commit history

### PCI DSS

**Control**: 6.4.6 Change Approval
**Evidence**: Multisig approvals for production changes

---

## Appendix: Approval Policy Schema

```yaml
version: 1

rules:
  - name: string                    # Rule name (required)
    glob: string                    # File glob pattern (required)
    required_approvers: int         # Minimum approvers (required)
    required_teams:                 # Teams that must approve (optional)
      - string
    min_per_team: int               # Min approvers per team (default: 1)
    description: string             # Human-readable description (optional)
```

### Glob Patterns

- `*`: Match any characters (except `/`)
- `**`: Match any characters (including `/`)
- `?`: Match single character
- `{ext1,ext2}`: Match any of the extensions
- `[abc]`: Match any single character in set

**Examples**:
- `configs/policy/*.json` → All JSON files in `configs/policy/`
- `configs/policy/**/*.json` → All JSON files in `configs/policy/` and subdirectories
- `configs/policy/rbac*.{json,yaml}` → `rbac.json`, `rbac_map.yaml`, etc.

---

**Last Review**: 2025-11-16
**Next Review**: 2026-01-01 (or after approval process incident)
