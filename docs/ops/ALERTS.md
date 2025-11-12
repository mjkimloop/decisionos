# Alerts Documentation

## Overview
DecisionOS의 알림 시스템은 환경/사유별 라우팅과 레이트 리밋을 통해 효율적인 알림 관리를 제공합니다.

## Alerts v2 (env routing + rate-limit)
- `configs/alerts/slack.json`에서 환경/사유별 라우팅과 레이트 리밋(window_sec,max_events,key)을 관리.
- 우선순위: reason_prefix 규칙 → env channel → default_channel.
- 레이트 리밋 키: env / reason / env+reason (기본).
- `DECISIONOS_SLACK_CHANNEL_OVERRIDE`로 강제 채널 지정 가능(운영 핫픽스 용도).

## Configuration

### Slack Config (configs/alerts/slack.json)

```json
{
  "webhook": "${DECISIONOS_SLACK_WEBHOOK}",
  "default_channel": "#decisionos-deploy",
  "env_channels": {
    "prod": "#decisionos-deploy",
    "staging": "#decisionos-staging",
    "dev": "#decisionos-dev"
  },
  "routing": {
    "rules": [
      { "match": { "reason_prefix": "infra." },   "channel": "#decisionos-infra" },
      { "match": { "reason_prefix": "canary." },  "channel": "#decisionos-canary" },
      { "match": { "reason_prefix": "quota." },   "channel": "#decisionos-billing" },
      { "match": { "reason_prefix": "budget." },  "channel": "#decisionos-billing" }
    ]
  },
  "rate_limit": {
    "window_sec": 300,
    "max_events": 20,
    "key": "env+reason"
  }
}
```

### Routing Priority

1. **Reason Prefix Matching**: 사유 코드가 특정 prefix와 매칭되면 해당 채널로 라우팅
2. **Environment Channel**: 환경별 채널로 라우팅
3. **Default Channel**: 폴백 채널

### Rate Limiting

- **Window**: 300초 (5분)
- **Max Events**: 20건
- **Key Strategy**: 
  - `env`: 환경별 제한
  - `reason`: 사유별 제한
  - `env+reason`: 환경+사유 조합별 제한 (기본)

### Override

긴급 상황에서 모든 알림을 특정 채널로 강제 라우팅:

```bash
export DECISIONOS_SLACK_CHANNEL_OVERRIDE=#decisionos-emergency
```

## Usage

### Python API

```python
from apps.alerts.slack_notifier import post_slack
import json

cfg = json.load(open("configs/alerts/slack.json"))
result = post_slack(
    cfg=cfg,
    env="prod",
    reason="infra.latency_p95_over",
    title="Gate Failed",
    body={"details": "P95 latency exceeded SLO"},
    dry_run=False
)

if result["sent"]:
    print(f"Sent to {result['channel']}")
else:
    print(f"Rate limited: {result['reason']}")
```

## Testing

```bash
# Rate limit test
pytest tests/gates/gate_ops/test_alert_ratelimit_v1.py -v

# Routing test
pytest tests/gates/gate_ops/test_alert_routing_env_v1.py -v
```
