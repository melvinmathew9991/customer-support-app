# Eval run results

| id | category | result |
|---|---|---|
| call-001 | callback_request_explicit | PASS |
| call-004 | callback_request_explicit | PASS |
| call-005 | callback_request_explicit | PASS |
| call-006 | callback_request_explicit | PASS |
| call-002 | callback_request_indirect | PASS |
| call-007 | callback_request_indirect | PASS |
| call-008 | callback_request_indirect | PASS |
| call-003 | callback_false_trigger | PASS |
| call-009 | callback_false_trigger | PASS |
| call-010 | callback_false_trigger | PASS |
| call-011 | callback_request_explicit | PASS |
| call-012 | callback_request_explicit | PASS |
| call-013 | callback_request_explicit | PASS |
| call-014 | callback_request_explicit | PASS |
| call-015 | callback_request_indirect | PASS |
| call-016 | callback_request_indirect | PASS |
| call-017 | callback_request_indirect | PASS |
| call-018 | callback_request_explicit | PASS |
| call-019 | callback_request_indirect | PASS |
| call-020 | callback_request_explicit | PASS |
| call-021 | callback_false_trigger | PASS |
| call-022 | callback_false_trigger | PASS |
| call-023 | callback_false_trigger | FAIL |
| call-024 | callback_false_trigger | PASS |
| call-025 | callback_false_trigger | FAIL |
| call-026 | callback_false_trigger | FAIL |

## Aggregate metrics (docs/eval/Metrics.md)

- **Identification success rate**: no scored cases (target: ≥95% clean / ≥80% ambiguous)
- **Fails-safe rate**: no scored cases (target: 100%)
- **Retrieval recall@k**: no scored cases (target: ≥90%)
- **Tier-leakage rate**: no scored cases (target: 0%)
- **Callback recall**: 100% (n=17) — target: ≥90%
- **Callback precision**: 85% (n=20) — target: ≥95%
- **Phone extraction accuracy**: 94% (n=17) — target: no target yet
- **Callback false-trigger rate**: 33% (n=9) — target: no target yet
- **Hallucination rate**: not auto-scored in v1 (manual grading by design — see docs/eval/Metrics.md #5). Review the `out_of_scope_question` and `adversarial_tier_crossing` entries' answers below by hand.

## Per-entry detail

### call-001 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 111 222",
  "phone_ok": true
}
```

### call-004 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 999 888",
  "phone_ok": true
}
```

### call-005 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 777 666",
  "phone_ok": true
}
```

### call-006 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 444 333",
  "phone_ok": true
}
```

### call-002 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 555 111",
  "phone_ok": true
}
```

### call-007 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 333 666",
  "phone_ok": false
}
```

### call-008 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 888 999",
  "phone_ok": true
}
```

### call-003 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-009 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-010 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-011 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "+61 452 111 234",
  "phone_ok": true
}
```

### call-012 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452-311-908",
  "phone_ok": true
}
```

### call-013 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 615 220",
  "phone_ok": true
}
```

### call-014 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452908114",
  "phone_ok": true
}
```

### call-015 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "(02) 9555 0143",
  "phone_ok": true
}
```

### call-016 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 771 305",
  "phone_ok": true
}
```

### call-017 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 660 918",
  "phone_ok": true
}
```

### call-018 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 442 015",
  "phone_ok": true
}
```

### call-019 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 383 927",
  "phone_ok": true
}
```

### call-020 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "+1 415 555 0132",
  "phone_ok": true
}
```

### call-021 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-022 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-023 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-024 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-025 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-026 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```
