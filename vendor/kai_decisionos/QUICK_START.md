# Quick Start Guide: Rule DSL & Offline Evaluation

## Installation

```bash
cd kai-decisionos
pip install -e .
```

## Rule Evaluation

### Command Line Evaluation

```bash
# Create a test payload
echo '{"credit_score": 720, "dti": 0.30, "income_verified": true}' > test_payload.json

# Evaluate rules
python -m apps.rule_engine.eval_rule \
  packages/rules/triage/lead_triage.yaml \
  test_payload.json \
  --pretty

# With AST introspection (for debugging)
python -m apps.rule_engine.eval_rule \
  packages/rules/triage/lead_triage.yaml \
  test_payload.json \
  --show-ast \
  --pretty
```

### Expected Output

```json
{
  "ruleset": {
    "name": "lead_triage_rules",
    "version": "1.0.0"
  },
  "outcome": {
    "class": "approve",
    "reasons": ["strong_credit_and_low_dti"],
    "confidence": 0.92,
    "required_docs": [],
    "rules_applied": ["approve_strong"]
  },
  "total_rules": 6,
  "rules_evaluated": 1
}
```

## Rule Linting

### Basic Linting

```bash
# Human-readable output
python -m apps.rule_engine.linter packages/rules/triage

# Output:
# === Lint Report ===
# Total rules analyzed: 6
#
# No issues found!
#
# === Coverage Summary ===
#   Rules with priority: 100.0%
#   Rules with stop flag: 50.0%
#   Rules with action.class: 100.0%
```

### JSON Output (for CI/CD)

```bash
# JSON output
python -m apps.rule_engine.linter packages/rules/triage --json

# With strict failure mode
python -m apps.rule_engine.linter packages/rules/triage --json --fail-on=any
```

### Failure Modes

- `--fail-on=conflict` (default) - Exit code 2 on conflicting rules
- `--fail-on=shadow` - Exit code 2 on shadowed rules
- `--fail-on=duplicate_name` - Exit code 2 on duplicate names
- `--fail-on=any` - Exit code 2 on any issues

## Offline Evaluation

### Run Simulation

```bash
# Evaluate against sample data
python -m cli.dosctl.main simulate lead_triage packages/samples/leads.csv

# Output shows metrics and confirms report generation:
# {'metrics': {'reject_precision': 1.0, 'reject_recall': 0.333, 'review_rate': 0.5}}
# HTML report: var/reports/simulate_lead_triage.html
# JSON metrics: var/reports/simulate_lead_triage.json
```

### Custom Output Paths

```bash
python -m cli.dosctl.main simulate lead_triage packages/samples/leads.csv \
  --html-out=my_report.html \
  --json-out=my_metrics.json
```

### Custom Label Column

```bash
python -m cli.dosctl.main simulate lead_triage packages/samples/leads.csv \
  --label-key=approved
```

## Report Outputs

### JSON Report Structure

```json
{
  "contract": "lead_triage",
  "timestamp": "2025-11-02T11:41:52.315425Z",
  "metrics": {
    "reject_precision": 1.0,
    "reject_recall": 0.3333333333333333,
    "review_rate": 0.5
  },
  "metadata": {
    "total_rows": 6,
    "label_key": "converted",
    "csv_path": "packages/samples/leads.csv"
  }
}
```

### HTML Report Features

- **Responsive Design**: Adapts to mobile, tablet, desktop
- **Color-Coded KPIs**:
  - 🟢 Green: Good performance (≥90% for precision/recall, ≤20% for review rate)
  - 🟡 Yellow: Warning (70-90% / 20-40%)
  - 🔴 Red: Needs attention (<70% / >40%)
- **Progress Bars**: Visual representation of metric values
- **Metadata Section**: Shows evaluation details (row count, label key, source file)

## Writing Rules

### Rule YAML Structure

```yaml
name: my_ruleset
version: 1.0.0
rules:
  - name: rule_name
    when: 'payload.get("field", default) > threshold'
    priority: 10        # Higher = evaluated first (optional, default: 0)
    stop: true          # Stop after this rule if matched (optional, default: false)
    action:
      class: approve    # approve | reject | review
      reasons:
        - "reason_text"
      confidence: 0.9   # 0.0 - 1.0
      required_docs:    # Optional, for review class
        - "document_type"
```

### Expression Syntax

**Allowed Operations:**
- Comparisons: `>`, `<`, `>=`, `<=`, `==`, `!=`
- Boolean: `and`, `or`, `not`
- Arithmetic: `+`, `-`, `*`, `/`
- Field access: `payload.get("field", default_value)`

**Security Restrictions:**
- Only `payload.get()` method calls allowed
- No arbitrary Python code execution
- No file I/O or network operations
- No imports or dangerous built-ins

**Examples:**

```yaml
# Simple threshold
when: 'payload.get("credit_score", 0) >= 700'

# Multiple conditions
when: 'payload.get("credit_score", 0) >= 700 and payload.get("dti", 1.0) <= 0.35'

# Boolean field check
when: 'payload.get("income_verified", False)'

# Negative conditions
when: 'not payload.get("flagged", False) and payload.get("score", 0) > 50'
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Rule DSL tests (35 tests)
pytest tests/test_rule_dsl_comprehensive.py -v

# Offline eval tests (11 tests)
pytest tests/test_offline_eval_comprehensive.py -v

# Coverage report
pytest tests/test_rule_dsl_comprehensive.py \
       tests/test_offline_eval_comprehensive.py \
       tests/test_engine_eval.py \
       tests/test_linter.py \
       --cov=apps.rule_engine \
       --cov-report=term
```

### Run Specific Test

```bash
pytest tests/test_rule_dsl_comprehensive.py::test_evaluate_single_matching_rule -v
```

## Common Use Cases

### 1. Develop and Test New Rules

```bash
# 1. Write rules in YAML
vim packages/rules/triage/my_rules.yaml

# 2. Lint for issues
python -m apps.rule_engine.linter packages/rules/triage --json

# 3. Test with sample payload
echo '{"field": value}' > test.json
python -m apps.rule_engine.eval_rule packages/rules/triage/my_rules.yaml test.json --pretty

# 4. Evaluate against historical data
python -m cli.dosctl.main simulate my_contract historical_data.csv
```

### 2. CI/CD Integration

```bash
# In your CI pipeline:

# Lint rules (fail on conflicts)
python -m apps.rule_engine.linter packages/rules/triage --json --fail-on=conflict || exit 1

# Run tests
pytest tests/ -q || exit 1

# Generate metrics report
python -m cli.dosctl.main simulate lead_triage packages/samples/leads.csv

# Archive reports
tar -czf reports.tar.gz var/reports/
```

### 3. Performance Analysis

```bash
# Run simulation against different datasets
for dataset in train.csv validation.csv test.csv; do
  python -m cli.dosctl.main simulate lead_triage "$dataset" \
    --html-out="var/reports/$(basename $dataset .csv)_report.html" \
    --json-out="var/reports/$(basename $dataset .csv)_metrics.json"
done

# Compare metrics
cat var/reports/*_metrics.json | jq '.metrics'
```

## Troubleshooting

### Issue: "No such file or directory: contract.json"

**Solution**: Ensure contract file exists in `packages/contracts/` directory.

```bash
ls packages/contracts/
# Should show: lead_triage.contract.json
```

### Issue: "Disallowed expression node"

**Solution**: Your rule expression uses unsafe operations. Use only allowed syntax:

```yaml
# ✅ Correct
when: 'payload.get("score", 0) > 50'

# ❌ Wrong - arbitrary function calls
when: 'calculate_score(payload)'

# ❌ Wrong - attribute access
when: 'payload.score'
```

### Issue: "Rules have conflicts"

**Solution**: Check linter output and resolve conflicting rules:

```bash
python -m apps.rule_engine.linter packages/rules/triage
```

Common conflicts:
- Same condition, different actions
- Shadowed rules (earlier rule with stop=true blocks later rules)

### Issue: Unicode encoding error on Windows

**Solution**: The reports generate successfully despite the console error. Check output files:

```bash
# Verify files were created
ls -l var/reports/

# View JSON metrics
cat var/reports/simulate_lead_triage.json

# Open HTML in browser
start var/reports/simulate_lead_triage.html
```

## Directory Structure

```
kai-decisionos/
├── apps/
│   └── rule_engine/
│       ├── engine.py           # Core evaluation engine
│       ├── eval_rule.py        # CLI evaluator
│       ├── linter.py           # Rule linter
│       ├── offline_eval.py     # Offline evaluation harness
│       └── templates/
│           └── report.html     # HTML report template
├── cli/
│   └── dosctl/
│       └── main.py             # dosctl simulate command
├── packages/
│   ├── contracts/              # Contract definitions
│   ├── rules/                  # Rule YAML files
│   │   └── triage/
│   │       └── lead_triage.yaml
│   └── samples/                # Sample data
│       └── leads.csv
├── tests/
│   ├── test_rule_dsl_comprehensive.py      # 35 tests
│   └── test_offline_eval_comprehensive.py  # 11 tests
└── var/
    └── reports/                # Generated reports
        ├── simulate_*.html
        └── simulate_*.json
```

## Next Steps

1. **Explore sample rules**: `cat packages/rules/triage/lead_triage.yaml`
2. **Run linter**: `python -m apps.rule_engine.linter packages/rules/triage`
3. **Generate report**: `python -m cli.dosctl.main simulate lead_triage packages/samples/leads.csv`
4. **View HTML report**: Open `var/reports/simulate_lead_triage.html` in browser
5. **Run tests**: `pytest tests/test_rule_dsl_comprehensive.py -v`

## Additional Resources

- **Full Documentation**: See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Test Examples**: Browse `tests/test_rule_dsl_comprehensive.py` for usage patterns
- **Rule Examples**: See `packages/rules/triage/lead_triage.yaml` for reference
