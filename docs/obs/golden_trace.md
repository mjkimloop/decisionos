# Golden Trace Harness (v0.5.10c)

Golden Trace는 Witness/Backfill/CLI Judge 스모크를 한 번에 실행하기 위한 샘플 번들입니다.

## 생성

```
python apps/obs/calibration/golden_trace.py --p95 1200 --err 0.01 --n 1000
```

산출물 (`evidence/golden/`)

| 파일 | 설명 |
| --- | --- |
| `raw_events.jsonl` | 합성 이벤트 (latency_ms, err, cite_ok, cost, parity_delta) |
| `witness.json` | exporter_x 기반 witness (seal 포함) |

## 검증 흐름

1. **Backfill Reconcile**
   ```
   python jobs/obs/reconcile/backfill_runner.py \
     --witness evidence/golden/witness.json \
     --raw evidence/golden/raw_events.jsonl \
     --slo configs/slo/slo.json
   ```
   - `backfill_report.json`, `discrepancies.csv` 생성 (동일 디렉터리).

2. **CLI Judge (DSL)**
   ```
   python cli/dosctl/exp_judge.py \
     --witness evidence/golden/witness.json \
     --slo configs/slo/slo.json
   ```
   - `verdicts_cli.json` 생성. `--expr` 옵션으로 ad-hoc DSL 평가 가능.

## 참고

- measurement_quorum_tolerances는 `configs/slo/slo.json`에서 관리합니다.
- Evidence 결과는 `docs/TechSpec.md`의 Gate-AJ/T v0.5.10c 섹션에 기록합니다.
