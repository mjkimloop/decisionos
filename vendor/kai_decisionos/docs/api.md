# API Documentation

This document details the API endpoints for DecisionOS.

**Authentication**: All endpoints require a Bearer token. See the [Runbook](runbook.md) for details on test tokens.

---

## 1. Decide

- **Endpoint**: `POST /decide`
- **Permission**: `user`
- **Description**: Evaluates a lead against the rules defined in the `lead_triage` contract and returns a decision.

**Sample Request**:

```json
{
  "org_id": "orgA",
  "payload": {
    "org_id": "orgA",
    "credit_score": 720,
    "dti": 0.3,
    "income_verified": true
  }
}
```

**Sample Response** (200 OK):

```json
{
  "action": {
    "class": "approve",
    "reasons": ["strong_credit_and_low_dti"],
    "confidence": 0.92,
    "required_docs": []
  },
  "decision_id": "<unique_decision_id>"
}
```

---

## 2. Simulate

- **Endpoint**: `POST /simulate`
- **Permission**: `admin`
- **Description**: Runs a simulation with a batch of payloads to evaluate the performance of the rule set.

**Sample Request**:

```json
{
  "org_id": "orgA",
  "payloads": [
    {
      "org_id": "orgA",
      "credit_score": 720,
      "dti": 0.3,
      "income_verified": true
    },
    {
      "org_id": "orgB",
      "credit_score": 540,
      "dti": 0.4,
      "income_verified": true
    }
  ]
}
```

**Sample Response** (200 OK):

```json
{
  "metrics": {
    "approve_rate": 0.5,
    "reject_rate": 0.5,
    "total_processed": 2
  }
}
```

---

## 3. Explain

- **Endpoint**: `GET /explain?decision_id={decision_id}`
- **Permission**: `admin`
- **Description**: Provides detailed information about how a specific decision was made.

**Sample Request**:

```
GET /explain?decision_id=a1b2c3d4
```

**Sample Response** (200 OK):

```json
{
  "rules_applied": ["approve_strong"],
  "model_meta": {},
  "input_hash": "<hash_of_input>",
  "output_hash": "<hash_of_output>",
  "timestamp": "2023-10-27T10:00:00Z"
}
```

---

## 4. Consent

- **Endpoint**: `POST /consent`
- **Permission**: `user`
- **Description**: Updates user consent preferences.

**Sample Request**:

```json
{
  "user_id": "user123",
  "consents": {
    "marketing_emails": true,
    "data_sharing": false
  }
}
```

**Sample Response** (200 OK):

```json
{
  "status": "consent updated",
  "user_id": "user123"
}
```