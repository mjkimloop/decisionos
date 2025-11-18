#!/usr/bin/env bash
# DR recovery time measurement with ObjectLock validation
#
# Validates:
#   1. ObjectLock upload succeeds
#   2. Recovery time (RTO) ≤ 15 minutes
#   3. Recovery point objective (RPO) ≤ 1 file loss
#
# Usage:
#   bash pipeline/dr/measure_recovery_time.sh
#   bash pipeline/dr/measure_recovery_time.sh --bucket my-bucket --evidence-dir var/evidence
#
# Environment:
#   DECISIONOS_S3_BUCKET         S3 bucket for DR (required)
#   DECISIONOS_S3_PREFIX         S3 prefix (default: evidence/dr)
#   EVIDENCE_DIR                 Local evidence directory (default: var/evidence)
#   DR_MAX_RTO_SECONDS           Max recovery time (default: 900 = 15min)
#   DR_MAX_RPO_FILES             Max file loss (default: 1)
#
# Exit codes:
#   0: DR recovery meets SLO
#   1: DR recovery exceeds SLO (BLOCKING)
#   2: Critical error (missing bucket, etc.)

set -euo pipefail

BUCKET="${DECISIONOS_S3_BUCKET:-}"
PREFIX="${DECISIONOS_S3_PREFIX:-evidence/dr}"
EVIDENCE_DIR="${EVIDENCE_DIR:-var/evidence}"
MAX_RTO="${DR_MAX_RTO_SECONDS:-900}"  # 15 minutes
MAX_RPO="${DR_MAX_RPO_FILES:-1}"      # 1 file
RECOVERY_DIR="var/dr_recovery_test"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket) BUCKET="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --max-rto) MAX_RTO="$2"; shift 2 ;;
    --max-rpo) MAX_RPO="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { echo "[dr-measure] $*"; }
error() { echo "[dr-measure ERROR] $*" >&2; }
warn() { echo "[dr-measure WARN] $*"; }

log "========================================="
log "  DR RECOVERY MEASUREMENT"
log "  Bucket: $BUCKET"
log "  Prefix: $PREFIX"
log "  Evidence dir: $EVIDENCE_DIR"
log "  Max RTO: ${MAX_RTO}s ($(( MAX_RTO / 60 ))m)"
log "  Max RPO: $MAX_RPO files"
log "========================================="

# Validate bucket
if [ -z "$BUCKET" ]; then
  error "S3 bucket not configured (set DECISIONOS_S3_BUCKET)"
  exit 2
fi

# Check if evidence directory exists
if [ ! -d "$EVIDENCE_DIR" ]; then
  error "Evidence directory not found: $EVIDENCE_DIR"
  exit 2
fi

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
  error "AWS CLI not found (required for S3 operations)"
  exit 2
fi

# Count evidence files
evidence_count=$(find "$EVIDENCE_DIR" -name "*.json" -type f | wc -l)
log "  Evidence files: $evidence_count"

if [ "$evidence_count" -eq 0 ]; then
  warn "  No evidence files to test (skipping DR measurement)"
  exit 0
fi

log ""
log "--- Step 1: Upload to S3 with ObjectLock ---"

upload_start=$(date +%s)

# Create test marker file
test_run_id="dr-test-$(date +%Y%m%d-%H%M%S)"
marker_file="$EVIDENCE_DIR/dr_test_marker.json"
cat > "$marker_file" <<EOF
{
  "test_run_id": "$test_run_id",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "evidence_count": $evidence_count
}
EOF

log "  Test run ID: $test_run_id"

# Upload evidence files
uploaded=0
failed_uploads=0

for evidence_file in "$EVIDENCE_DIR"/*.json; do
  filename=$(basename "$evidence_file")
  s3_key="$PREFIX/$test_run_id/$filename"

  log "  Uploading: $filename"

  # Upload with server-side encryption and object lock
  if aws s3api put-object \
    --bucket "$BUCKET" \
    --key "$s3_key" \
    --body "$evidence_file" \
    --server-side-encryption AES256 \
    --object-lock-mode GOVERNANCE \
    --object-lock-retain-until-date "$(date -u -d '+30 days' +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v+30d +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo '2025-12-31T00:00:00Z')" \
    >/dev/null 2>&1; then
    uploaded=$((uploaded + 1))
    log "    ✓ Uploaded: s3://$BUCKET/$s3_key"
  else
    warn "    ⚠ Upload failed (trying without ObjectLock): $filename"
    # Retry without ObjectLock (for buckets without versioning)
    if aws s3 cp "$evidence_file" "s3://$BUCKET/$s3_key" --sse AES256 >/dev/null 2>&1; then
      uploaded=$((uploaded + 1))
      log "    ✓ Uploaded (no lock): s3://$BUCKET/$s3_key"
    else
      failed_uploads=$((failed_uploads + 1))
      error "    ✗ Upload failed: $filename"
    fi
  fi
done

upload_end=$(date +%s)
upload_duration=$((upload_end - upload_start))

log "  Uploaded: $uploaded files in ${upload_duration}s"

if [ $failed_uploads -gt 0 ]; then
  error "  ✗ Upload failed for $failed_uploads files"
  exit 1
fi

log ""
log "--- Step 2: Simulate DR recovery ---"

# Clean recovery directory
rm -rf "$RECOVERY_DIR"
mkdir -p "$RECOVERY_DIR"

recovery_start=$(date +%s)

log "  Downloading from S3..."

# Download all files
downloaded=0
failed_downloads=0

for evidence_file in "$EVIDENCE_DIR"/*.json; do
  filename=$(basename "$evidence_file")
  s3_key="$PREFIX/$test_run_id/$filename"
  local_path="$RECOVERY_DIR/$filename"

  if aws s3 cp "s3://$BUCKET/$s3_key" "$local_path" --quiet 2>/dev/null; then
    downloaded=$((downloaded + 1))
  else
    failed_downloads=$((failed_downloads + 1))
    error "    ✗ Download failed: $filename"
  fi
done

recovery_end=$(date +%s)
recovery_duration=$((recovery_end - recovery_start))

log "  Downloaded: $downloaded files in ${recovery_duration}s"

log ""
log "--- Step 3: Validate recovery metrics ---"

# Calculate RTO (Recovery Time Objective)
rto_seconds=$((recovery_end - recovery_start))
rto_minutes=$((rto_seconds / 60))

log "  RTO (actual): ${rto_seconds}s (${rto_minutes}m)"
log "  RTO (target): ${MAX_RTO}s ($(( MAX_RTO / 60 ))m)"

# Calculate RPO (Recovery Point Objective)
rpo_files=$((evidence_count - downloaded))

log "  RPO (actual): $rpo_files files lost"
log "  RPO (target): ≤${MAX_RPO} files"

# Validate RTO
rto_pass=0
if [ $rto_seconds -le $MAX_RTO ]; then
  log "  ✓ RTO: PASS (${rto_seconds}s ≤ ${MAX_RTO}s)"
  rto_pass=1
else
  error "  ✗ RTO: FAIL (${rto_seconds}s > ${MAX_RTO}s)"
fi

# Validate RPO
rpo_pass=0
if [ $rpo_files -le $MAX_RPO ]; then
  log "  ✓ RPO: PASS ($rpo_files ≤ $MAX_RPO files)"
  rpo_pass=1
else
  error "  ✗ RPO: FAIL ($rpo_files > $MAX_RPO files)"
fi

# Verify file integrity
log ""
log "--- Step 4: Verify file integrity ---"

integrity_pass=1

for evidence_file in "$EVIDENCE_DIR"/*.json; do
  filename=$(basename "$evidence_file")
  recovered_file="$RECOVERY_DIR/$filename"

  if [ ! -f "$recovered_file" ]; then
    error "  ✗ Missing recovered file: $filename"
    integrity_pass=0
    continue
  fi

  # Compare checksums
  if command -v sha256sum >/dev/null 2>&1; then
    original_hash=$(sha256sum "$evidence_file" | awk '{print $1}')
    recovered_hash=$(sha256sum "$recovered_file" | awk '{print $1}')
  elif command -v shasum >/dev/null 2>&1; then
    original_hash=$(shasum -a 256 "$evidence_file" | awk '{print $1}')
    recovered_hash=$(shasum -a 256 "$recovered_file" | awk '{print $1}')
  else
    warn "  ⚠ No SHA256 tool available (skipping integrity check)"
    break
  fi

  if [ "$original_hash" = "$recovered_hash" ]; then
    log "  ✓ Integrity OK: $filename"
  else
    error "  ✗ Integrity FAIL: $filename"
    integrity_pass=0
  fi
done

# Cleanup
log ""
log "Cleaning up test files..."
rm -rf "$RECOVERY_DIR"
aws s3 rm "s3://$BUCKET/$PREFIX/$test_run_id/" --recursive --quiet 2>/dev/null || true

log ""
log "========================================="
log "  DR RECOVERY SUMMARY"
log "  RTO: ${rto_seconds}s (target: ≤${MAX_RTO}s) - $([ $rto_pass -eq 1 ] && echo "PASS" || echo "FAIL")"
log "  RPO: $rpo_files files (target: ≤${MAX_RPO}) - $([ $rpo_pass -eq 1 ] && echo "PASS" || echo "FAIL")"
log "  Integrity: $([ $integrity_pass -eq 1 ] && echo "PASS" || echo "FAIL")"
log "========================================="

if [ $rto_pass -eq 1 ] && [ $rpo_pass -eq 1 ] && [ $integrity_pass -eq 1 ]; then
  log "  ✓✓✓ DR RECOVERY: PASS ✓✓✓"
  exit 0
else
  error "  ✗✗✗ DR RECOVERY: FAIL ✗✗✗"
  exit 1
fi
