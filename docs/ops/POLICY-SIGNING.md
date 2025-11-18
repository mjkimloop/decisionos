# Policy Signing and Verification

**Owner**: Platform Security
**Updated**: 2025-11-16
**Version**: v0.5.11v

---

## Overview

All DecisionOS policy files MUST be cryptographically signed before deployment. This ensures:

- **Integrity**: Policies cannot be tampered with
- **Authenticity**: Policies come from authorized signers
- **Auditability**: Full chain of custody for policy changes
- **Fail-Closed**: Unsigned policies are rejected by runtime

---

## Architecture

### Components

```
┌─────────────────┐
│  Policy Files   │  configs/policy/*.json
│  (unsigned)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  scripts/       │
│  policy/sign.py │  ← HMAC or KMS signing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  .sig Files     │  Signature metadata + HMAC
│  (sidecar)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Policy         │  configs/policy/registry.json
│  Registry       │  ← Root hash + chain
└────────┬────────┘
         │
         ├──────────────────┬─────────────────┐
         ▼                  ▼                 ▼
  ┌───────────┐      ┌──────────┐     ┌──────────┐
  │ CI Verify │      │ Runtime  │     │ Attest   │
  │  (Gate)   │      │  Loader  │     │  (Post)  │
  └───────────┘      └──────────┘     └──────────┘
```

---

## Signing Workflow

### 1. Sign Policy File

```bash
# Sign single file (HMAC)
python -m scripts.policy.sign configs/policy/slo.json

# Sign with specific key
python -m scripts.policy.sign configs/policy/slo.json --key-id k1

# Batch sign all policies
python -m scripts.policy.sign --batch configs/policy/*.json

# Sign with KMS (requires AWS credentials)
python -m scripts.policy.sign configs/policy/rbac.json \
  --kms-arn arn:aws:kms:us-east-1:123456789012:key/...
```

**Output**: `configs/policy/slo.json.sig`

```json
{
  "version": 1,
  "issuer": "platform",
  "created_at": "2025-11-16T10:00:00Z",
  "policy_file": "slo.json",
  "sha256": "a1b2c3...",
  "algorithm": "hmac-sha256",
  "key_id": "k1",
  "signature": "dGVzdC1zaWduYXR1cmU..."
}
```

### 2. Update Registry

```bash
# Scan policies and update registry
python -m scripts.policy.registry update

# Verify hash chain integrity
python -m scripts.policy.registry verify-chain

# Show registry contents
python -m scripts.policy.registry show
```

**Registry Structure** (`configs/policy/registry.json`):

```json
{
  "version": 1,
  "root_hash": "a1b2c3d4...",
  "entries": [
    {
      "file": "slo.json",
      "sha256": "e5f6g7...",
      "key_id": "k1",
      "created_at": "2025-11-16T10:00:00Z"
    }
  ],
  "allowed_keys": [
    {
      "key_id": "k1",
      "state": "active",
      "added_at": "2025-01-01T00:00:00Z"
    }
  ],
  "chain": [
    {
      "root_hash": "a1b2c3...",
      "timestamp": "2025-11-16T10:00:00Z",
      "prev_root_hash": "h8i9j0..."
    }
  ]
}
```

### 3. Verify Signatures

```bash
# Verify single file
python -m scripts.policy.verify configs/policy/slo.json

# Batch verify
python -m scripts.policy.verify --batch configs/policy/*.json

# Strict mode (fail on warnings)
python -m scripts.policy.verify --strict configs/policy/slo.json

# Allow unsigned (NOT recommended for production)
python -m scripts.policy.verify --fail-open configs/policy/canary.json
```

**Exit Codes**:
- `0`: All checks passed
- `1`: Verification failed
- `8`: Warnings (soft fail)

---

## Runtime Enforcement

### Policy Loader (Fail-Closed)

All runtime policy loading uses `apps/common/policy_loader.py`:

```python
from apps.common.policy_loader import PolicyLoader, PolicySignatureError

loader = PolicyLoader()

try:
    policy = loader.load("configs/policy/slo.json", scope="slo")
except PolicySignatureError as e:
    # Signature verification failed - policy REJECTED
    logger.error(f"Policy verification failed: {e}")
    raise
```

**Features**:
- **Fail-closed by default**: Unsigned/invalid policies are rejected
- **Allowlist enforcement**: `DECISIONOS_POLICY_ALLOWLIST` restricts signing keys
- **Scope-based access**: `DECISIONOS_ALLOW_SCOPES` limits loader access
- **Audit logging**: All verification failures are logged

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DECISIONOS_POLICY_KEYS_JSON` | Yes* | - | HMAC MultiKey config JSON |
| `DECISIONOS_POLICY_KMS_KEY_ARN` | No | - | KMS key ARN (overrides HMAC) |
| `DECISIONOS_POLICY_ALLOWLIST` | No | (all) | Comma-separated allowed key_ids |
| `DECISIONOS_ALLOW_SCOPES` | No | (all) | Comma-separated allowed scopes |
| `DECISIONOS_POLICY_FAIL_OPEN` | No | 0 | 1=allow unsigned (NOT for prod) |

*Note: Falls back to `DECISIONOS_JUDGE_KEYS` if not set

---

## CI Integration

### Pre-Gate: Verify Changed Files

```yaml
- name: Verify policy signatures
  run: |
    CHANGED=$(git diff --name-only origin/main...HEAD | grep "configs/policy/.*\.json$" || true)
    if [ -n "$CHANGED" ]; then
      for file in $CHANGED; do
        python -m scripts.policy.verify "$file" --strict
      done
    fi
```

### Gate: Update Registry + Verify Chain

```yaml
- name: Update policy registry
  run: python -m scripts.policy.registry update

- name: Verify hash chain
  run: python -m scripts.policy.registry verify-chain
```

### Post-Gate: Attach Attestation

```yaml
- name: Generate build attestation
  run: python -m scripts.ci.attest_build

- name: Verify attestation
  run: python -m scripts.ci.verify_attestation --commit ${{ github.sha }}
```

---

## Key Management

### HMAC MultiKey Format

```bash
export DECISIONOS_POLICY_KEYS_JSON='[
  {
    "key_id": "k1",
    "secret": "base64-encoded-secret",
    "state": "active",
    "not_before": "2025-01-01T00:00:00Z",
    "not_after": "2026-01-01T00:00:00Z"
  },
  {
    "key_id": "k2",
    "secret": "base64-encoded-secret",
    "state": "grace",
    "not_before": "2025-11-01T00:00:00Z",
    "not_after": "2026-03-01T00:00:00Z"
  }
]'
```

### Key Rotation

See [POLICY-ROTATION.md](POLICY-ROTATION.md) for full rotation procedures.

**Quick Steps**:
1. Generate new key: `openssl rand -base64 32 > k2.secret`
2. Add to `DECISIONOS_POLICY_KEYS_JSON` with `state: grace`
3. Re-sign policies: `python -m scripts.policy.sign --batch --key-id k2 configs/policy/*.json`
4. Update registry: `python -m scripts.policy.registry update`
5. Deploy with overlap period (7+ days)
6. Transition to `active`, retire old key

### Allowlist Configuration

Restrict which keys can sign policies:

```bash
export DECISIONOS_POLICY_ALLOWLIST="k1,k2"
```

Unsigned policies signed with `k3` will be rejected even if `k3` is valid.

---

## Troubleshooting

### Error: "signature missing"

**Cause**: Policy file has no corresponding `.sig` file.

**Fix**:
```bash
python -m scripts.policy.sign configs/policy/slo.json
```

### Error: "signature mismatch"

**Cause**: Policy file was modified after signing.

**Fix**: Re-sign the file:
```bash
python -m scripts.policy.sign configs/policy/slo.json
python -m scripts.policy.registry update
```

### Error: "unknown policy key_id=k3"

**Cause**: Signature was created with key `k3` but it's not in `DECISIONOS_POLICY_KEYS_JSON`.

**Fix**: Add the key or re-sign with a known key:
```bash
python -m scripts.policy.sign configs/policy/slo.json --key-id k1
```

### Error: "Key not in allowlist"

**Cause**: `DECISIONOS_POLICY_ALLOWLIST` is set and key_id is not included.

**Fix**: Add key to allowlist or use an allowed key:
```bash
export DECISIONOS_POLICY_ALLOWLIST="k1,k2,k3"
```

### Warning: "Chain verification failed"

**Cause**: Registry hash chain has a break (prev_root_hash mismatch).

**Fix**: This indicates tampering or corruption. Investigate immediately:
```bash
python -m scripts.policy.registry verify-chain
python -m scripts.policy.registry show | jq '.chain'
```

---

## Security Best Practices

### DO ✅

- **Always sign policies** before committing to Git
- **Update registry** after signing
- **Verify chain integrity** in CI
- **Use fail-closed mode** in production (`DECISIONOS_POLICY_FAIL_OPEN=0`)
- **Rotate keys regularly** (every 90 days)
- **Audit signature keys** (log all signing operations)

### DON'T ❌

- **Never commit unsigned policies** to main branch
- **Never use fail-open mode** in production (emergency only)
- **Never share signing keys** across environments (dev/staging/prod)
- **Never skip registry update** after signing
- **Never ignore chain verification failures**

---

## Emergency Procedures

### Lost Signing Keys

1. **Immediate**: Enable fail-open mode (temporary):
   ```bash
   export DECISIONOS_POLICY_FAIL_OPEN=1
   ```

2. **Generate new keys**:
   ```bash
   openssl rand -base64 32 > k-emergency.secret
   ```

3. **Re-sign all policies** with new key

4. **Update registry** and deploy

5. **Disable fail-open** once verified

### Compromised Signing Key

1. **Revoke key immediately**: Set `state: retired` in `DECISIONOS_POLICY_KEYS_JSON`

2. **Audit all policies** signed with compromised key:
   ```bash
   jq '.entries[] | select(.key_id=="k-compromised")' configs/policy/registry.json
   ```

3. **Re-sign with new key**:
   ```bash
   python -m scripts.policy.sign --batch --key-id k-new configs/policy/*.json
   ```

4. **Force registry rebuild**:
   ```bash
   python -m scripts.policy.registry update
   ```

5. **Incident report**: Document timeline and affected policies

---

## Appendix: Signature Algorithm Details

### HMAC-SHA256

**Input**: Policy file SHA256 hash (hex string)
**Key**: Base64-decoded secret from `DECISIONOS_POLICY_KEYS_JSON`
**Output**: Base64-encoded HMAC-SHA256 signature

```python
import base64, hashlib, hmac

# Compute policy hash
with open("policy.json", "rb") as f:
    policy_hash = hashlib.sha256(f.read()).hexdigest()

# Sign hash
secret = base64.b64decode("your-base64-secret")
payload = policy_hash.encode("utf-8")
signature = hmac.new(secret, payload, hashlib.sha256).digest()
signature_b64 = base64.b64encode(signature).decode("ascii")
```

### KMS-RSA-SHA256 (Planned)

**Status**: Not yet implemented (stub in codebase)
**Algorithm**: RSA-2048 with SHA256
**Key Storage**: AWS KMS
**Signature Format**: Base64-encoded RSA signature

---

**Last Review**: 2025-11-16
**Next Review**: 2026-01-01 (or after key rotation incident)
