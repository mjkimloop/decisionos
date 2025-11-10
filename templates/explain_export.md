# Decision Explanation Export Template

## PDF/JSON Export Format

이 템플릿은 의사결정 설명(Explanation)을 고객 또는 규제 기관에 제출하기 위한 표준 형식을 정의합니다.

---

## 결정 설명서 (Decision Explanation Report)

### 문서 정보
- **보고서 ID**: `{report_id}`
- **생성 일시**: `{generated_at}`
- **의사결정 ID**: `{decision_id}`
- **요청자**: `{requester_name}` (`{requester_id}`)

---

## 1. 의사결정 요약 (Decision Summary)

### 결정 결과
- **결과**: `{outcome}` (승인/거부/검토)
- **결정 일시**: `{decision_timestamp}`
- **처리 시간**: `{processing_time_ms}` ms
- **신청 유형**: `{application_type}`

### 주요 정보
- **신청자**: `{applicant_name}` (ID: `{applicant_id_masked}`)
- **신청 금액**: `{requested_amount}` 원
- **제품/서비스**: `{product_name}`

---

## 2. 주요 사유 (Primary Reasons)

### 사유 코드 및 설명

#### 주요 사유 1
- **코드**: `{reason_code_1}`
- **설명**: `{reason_message_1}`
- **영향도**: `{impact_level_1}` (높음/중간/낮음)

**세부 내용**:
`{detailed_explanation_1}`

**개선 방안**:
`{improvement_advice_1}`

#### 주요 사유 2
- **코드**: `{reason_code_2}`
- **설명**: `{reason_message_2}`
- **영향도**: `{impact_level_2}`

**세부 내용**:
`{detailed_explanation_2}`

**개선 방안**:
`{improvement_advice_2}`

#### 주요 사유 3
- **코드**: `{reason_code_3}`
- **설명**: `{reason_message_3}`
- **영향도**: `{impact_level_3}`

**세부 내용**:
`{detailed_explanation_3}`

**개선 방안**:
`{improvement_advice_3}`

---

## 3. 영향 요인 분석 (Factor Attribution)

의사결정에 영향을 미친 주요 요인들입니다:

| 순위 | 요인 | 값 | 기여도 | 영향 |
|------|------|-----|--------|------|
| 1 | `{factor_1_name}` | `{factor_1_value}` | `{factor_1_contribution}` | `{factor_1_direction}` |
| 2 | `{factor_2_name}` | `{factor_2_value}` | `{factor_2_contribution}` | `{factor_2_direction}` |
| 3 | `{factor_3_name}` | `{factor_3_value}` | `{factor_3_contribution}` | `{factor_3_direction}` |
| 4 | `{factor_4_name}` | `{factor_4_value}` | `{factor_4_contribution}` | `{factor_4_direction}` |
| 5 | `{factor_5_name}` | `{factor_5_value}` | `{factor_5_contribution}` | `{factor_5_direction}` |

**범례**:
- 기여도: 해당 요인이 최종 결정에 미친 영향의 정도 (%)
- 영향: 긍정적(↑) 또는 부정적(↓)

### 요인 시각화
```
[차트/그래프 영역]
- 막대 그래프: 각 요인의 기여도
- 색상: 긍정적(녹색) / 부정적(빨간색)
```

---

## 4. 규칙 추적 (Rule Trace)

### 적용된 규칙

#### 규칙 1: `{rule_1_name}`
- **ID**: `{rule_1_id}`
- **조건**: `{rule_1_condition}`
- **결과**: `{rule_1_result}` (통과/실패)
- **점수 변화**: `{rule_1_score_impact}`

#### 규칙 2: `{rule_2_name}`
- **ID**: `{rule_2_id}`
- **조건**: `{rule_2_condition}`
- **결과**: `{rule_2_result}`
- **점수 변화**: `{rule_2_score_impact}`

### 불만족 규칙

#### 규칙: `{failed_rule_name}`
- **ID**: `{failed_rule_id}`
- **조건**: `{failed_rule_condition}`
- **실제 값**: `{failed_rule_actual_value}`
- **필요 값**: `{failed_rule_required_value}`
- **차이**: `{failed_rule_gap}`

---

## 5. 모델 정보 (Model Information)

### 사용된 모델
- **모델 이름**: `{model_name}`
- **모델 버전**: `{model_version}`
- **모델 유형**: `{model_type}` (규칙 기반/머신러닝/하이브리드)
- **훈련 일자**: `{model_trained_date}`
- **마지막 검증**: `{model_last_validated}`

### 모델 성능 지표
- **정확도**: `{model_accuracy}`
- **정밀도**: `{model_precision}`
- **재현율**: `{model_recall}`
- **AUC-ROC**: `{model_auc_roc}`

### 모델 해석 방법
이 결정의 설명은 다음 방법을 사용하여 생성되었습니다:
- **방법**: `{explanation_method}` (예: SHAP, LIME, Rule Trace)
- **충실도(Fidelity)**: `{explanation_fidelity}` (모델 예측과의 일치도)

---

## 6. 사용된 데이터 (Data Sources)

### 데이터 출처

| 데이터 유형 | 출처 | 수집 일시 | 상태 |
|-------------|------|-----------|------|
| `{data_type_1}` | `{data_source_1}` | `{data_collected_1}` | `{data_status_1}` |
| `{data_type_2}` | `{data_source_2}` | `{data_collected_2}` | `{data_status_2}` |
| `{data_type_3}` | `{data_source_3}` | `{data_collected_3}` | `{data_status_3}` |

### 데이터 품질
- **완전성**: `{data_completeness}` %
- **정확성**: `{data_accuracy}` %
- **신선도**: `{data_freshness}` (최신 데이터로부터 경과 시간)

### 개인정보 처리
- **수집 동의**: `{consent_obtained}` (예/아니오)
- **동의 일시**: `{consent_timestamp}`
- **보유 기간**: `{data_retention_period}`

---

## 7. 적용된 정책 (Applied Policies)

### 정책 정보
- **정책 이름**: `{policy_name}`
- **정책 버전**: `{policy_version}`
- **시행 일자**: `{policy_effective_date}`
- **정책 소유자**: `{policy_owner}`

### 주요 정책 항목
1. `{policy_item_1}`
2. `{policy_item_2}`
3. `{policy_item_3}`

### 규제 준수
- **준수 프레임워크**: `{compliance_frameworks}` (예: 신용정보법, 개인정보보호법)
- **감사 추적**: `{audit_trail_id}`

---

## 8. 유사 결정 사례 (Similar Decisions)

참고를 위한 유사한 의사결정 사례입니다 (개인정보는 익명화되었습니다):

### 사례 1
- **결정 ID**: `{similar_decision_1_id}`
- **결과**: `{similar_decision_1_outcome}`
- **유사도**: `{similar_decision_1_similarity}` %
- **주요 차이점**: `{similar_decision_1_difference}`

### 사례 2
- **결정 ID**: `{similar_decision_2_id}`
- **결과**: `{similar_decision_2_outcome}`
- **유사도**: `{similar_decision_2_similarity}` %
- **주요 차이점**: `{similar_decision_2_difference}`

### 사례 3
- **결정 ID**: `{similar_decision_3_id}`
- **결과**: `{similar_decision_3_outcome}`
- **유사도**: `{similar_decision_3_similarity}` %
- **주요 차이점**: `{similar_decision_3_difference}`

---

## 9. 다음 단계 (Next Steps)

### 귀하께서 취하실 수 있는 조치

#### 결과에 동의하는 경우
`{acceptance_next_steps}`

#### 결과에 이의가 있는 경우
`{dispute_next_steps}`

**이의 제기 방법**:
1. `{dispute_step_1}`
2. `{dispute_step_2}`
3. `{dispute_step_3}`

**이의 제기 기한**: `{dispute_deadline}`

#### 개선 후 재신청
`{reapplication_guidance}`

**권장 재신청 시기**: `{recommended_reapply_date}`

---

## 10. 법적 고지 (Legal Notice)

### 귀하의 권리
`{customer_rights_text}`

주요 권리:
- 결정에 대한 설명을 요청할 권리
- 부정확한 정보의 정정을 요구할 권리
- 의사결정에 이의를 제기할 권리
- 사용된 개인정보에 대한 열람 및 삭제를 요청할 권리

### 개인정보 보호
본 결정에 사용된 귀하의 개인정보는 [개인정보 처리방침]에 따라 보호됩니다.

- **개인정보 처리방침**: `{privacy_policy_url}`
- **데이터 보호 담당자**: `{dpo_contact}`

### 규제 정보
이 의사결정은 다음 법규를 준수합니다:
- `{regulation_1}`
- `{regulation_2}`
- `{regulation_3}`

### 면책 조항
`{disclaimer_text}`

---

## 11. 연락처 및 지원 (Contact & Support)

### 고객 지원
- **일반 문의**: `{customer_support_phone}` / `{customer_support_email}`
- **운영 시간**: `{support_hours}`
- **웹사이트**: `{support_website}`

### 컴플라이언스 및 이의 제기
- **컴플라이언스팀**: `{compliance_email}`
- **이의 제기 담당**: `{dispute_contact}`

### 추가 정보
- **FAQ**: `{faq_url}`
- **가이드**: `{guide_url}`

---

## 부록 (Appendix)

### A. 용어 정의

**신용점수 (Credit Score)**
`{credit_score_definition}`

**소득 대비 부채 비율 (DTI - Debt-to-Income Ratio)**
`{dti_definition}`

**총부채원리금상환비율 (DSR - Debt Service Ratio)**
`{dsr_definition}`

**기여도 (Contribution/Attribution)**
`{attribution_definition}`

### B. 계산 방법

**최종 스코어 계산**
```
최종 스코어 = (신용점수 × 0.4) + (소득 안정성 × 0.3) + (부채 비율 × 0.2) + (기타 × 0.1)
```

### C. 데이터 출처 상세

`{data_source_details}`

### D. 참조 문서
- 모델 카드: `{model_card_url}`
- 정책 문서: `{policy_document_url}`
- 감사 로그: `{audit_log_id}`

---

## 문서 메타데이터

### 생성 정보
- **템플릿 버전**: `{template_version}`
- **생성 시스템**: DecisionOS `{system_version}`
- **생성자**: `{generator_name}`
- **디지털 서명**: `{digital_signature}` (선택사항)

### 보안 분류
- **분류**: `{security_classification}` (Public/Internal/Confidential)
- **접근 권한**: `{access_permissions}`

### 문서 무결성
- **문서 해시**: `{document_hash}`
- **검증 방법**: `{verification_method}`

---

**이 문서는 자동 생성되었으며, DecisionOS의 Explainability 모듈에 의해 작성되었습니다.**

---

# JSON Export Format

PDF 대신 기계 판독 가능한 형식이 필요한 경우:

```json
{
  "report_metadata": {
    "report_id": "string",
    "generated_at": "ISO8601 timestamp",
    "decision_id": "string",
    "requester": {
      "name": "string",
      "id": "string",
      "role": "string"
    },
    "template_version": "string",
    "format_version": "1.0"
  },
  "decision_summary": {
    "outcome": "APPROVE|DENY|REVIEW",
    "decision_timestamp": "ISO8601 timestamp",
    "processing_time_ms": 0,
    "application_type": "string",
    "applicant": {
      "name": "string (masked)",
      "id": "string (masked)",
      "requested_amount": 0,
      "product_name": "string"
    }
  },
  "reason_codes": [
    {
      "code": "string",
      "message": "string",
      "category": "PRIMARY|CONTRIBUTING|INFORMATIONAL",
      "impact_level": "HIGH|MEDIUM|LOW",
      "detailed_explanation": "string",
      "improvement_advice": "string"
    }
  ],
  "factor_attribution": [
    {
      "rank": 0,
      "name": "string",
      "value": "string",
      "contribution_percent": 0.0,
      "direction": "POSITIVE|NEGATIVE|NEUTRAL"
    }
  ],
  "rule_trace": {
    "applied_rules": [
      {
        "rule_id": "string",
        "rule_name": "string",
        "condition": "string",
        "result": "PASS|FAIL",
        "score_impact": 0.0
      }
    ],
    "failed_rules": [
      {
        "rule_id": "string",
        "rule_name": "string",
        "condition": "string",
        "actual_value": "string",
        "required_value": "string",
        "gap": "string"
      }
    ]
  },
  "model_information": {
    "model_name": "string",
    "model_version": "string",
    "model_type": "RULE_BASED|ML|HYBRID",
    "trained_date": "ISO8601 date",
    "last_validated": "ISO8601 date",
    "performance_metrics": {
      "accuracy": 0.0,
      "precision": 0.0,
      "recall": 0.0,
      "auc_roc": 0.0
    },
    "explanation_method": "string",
    "explanation_fidelity": 0.0
  },
  "data_sources": [
    {
      "data_type": "string",
      "source": "string",
      "collected_at": "ISO8601 timestamp",
      "status": "VALID|STALE|MISSING"
    }
  ],
  "data_quality": {
    "completeness_percent": 0.0,
    "accuracy_percent": 0.0,
    "freshness": "string"
  },
  "applied_policies": [
    {
      "policy_name": "string",
      "policy_version": "string",
      "effective_date": "ISO8601 date",
      "policy_owner": "string",
      "key_items": ["string"]
    }
  ],
  "compliance": {
    "frameworks": ["string"],
    "audit_trail_id": "string"
  },
  "similar_decisions": [
    {
      "decision_id": "string (anonymized)",
      "outcome": "string",
      "similarity_percent": 0.0,
      "key_difference": "string"
    }
  ],
  "next_steps": {
    "acceptance_steps": "string",
    "dispute_steps": "string",
    "dispute_deadline": "ISO8601 date",
    "reapplication_guidance": "string",
    "recommended_reapply_date": "ISO8601 date"
  },
  "legal_notice": {
    "customer_rights": "string",
    "privacy_policy_url": "string",
    "dpo_contact": "string",
    "regulations": ["string"],
    "disclaimer": "string"
  },
  "contact_information": {
    "customer_support": {
      "phone": "string",
      "email": "string",
      "hours": "string",
      "website": "string"
    },
    "compliance": {
      "email": "string",
      "dispute_contact": "string"
    }
  },
  "appendix": {
    "definitions": {
      "term": "definition"
    },
    "calculation_methods": "string",
    "data_source_details": "string",
    "references": {
      "model_card_url": "string",
      "policy_document_url": "string",
      "audit_log_id": "string"
    }
  },
  "document_metadata": {
    "security_classification": "PUBLIC|INTERNAL|CONFIDENTIAL",
    "access_permissions": ["string"],
    "document_hash": "string",
    "digital_signature": "string"
  }
}
```

## 사용 예시

### Python 코드
```python
from decisionos.explainability import ExplanationExporter

# PDF 생성
exporter = ExplanationExporter(format='pdf', locale='ko')
pdf_bytes = exporter.export(
    decision_id='dec_20250103_abc123',
    include_sensitive=False,  # 고객 제출용은 민감정보 제외
    watermark='고객 제출용'
)

# 파일로 저장
with open('decision_explanation.pdf', 'wb') as f:
    f.write(pdf_bytes)

# JSON 생성
exporter = ExplanationExporter(format='json', locale='ko')
json_data = exporter.export(
    decision_id='dec_20250103_abc123'
)
```

### API 호출
```bash
# PDF 다운로드
curl -X POST https://api.decisionos.com/v1/decisions/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "dec_20250103_abc123",
    "format": "pdf",
    "locale": "ko",
    "include_sensitive": false
  }' \
  --output decision_explanation.pdf

# JSON 조회
curl -X POST https://api.decisionos.com/v1/decisions/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "dec_20250103_abc123",
    "format": "json",
    "locale": "ko"
  }'
```

## 버전 관리

| 버전 | 날짜 | 변경사항 |
|------|------|---------|
| 1.0 | 2025-11-03 | 초기 템플릿 생성 |
| 1.1 | TBD | 유사 결정 사례 섹션 추가 예정 |
| 1.2 | TBD | 시각화 개선 예정 |

## 관련 문서
- [Reason Codes Guide](../docs/reason_codes_ko.md)
- [Model Card Template](../docs/model_card_template.yaml)
- [Explainability Architecture](../docs/explainability_guide.md)
