# Eval run results

| id | category | result |
|---|---|---|
| call-037 | callback_false_trigger | PASS |
| call-038 | callback_false_trigger | FAIL |
| call-039 | callback_false_trigger | PASS |
| call-040 | callback_false_trigger | FAIL |
| call-041 | callback_false_trigger | PASS |
| call-042 | callback_false_trigger | FAIL |
| call-043 | callback_false_trigger | FAIL |
| call-044 | callback_false_trigger | PASS |
| call-045 | callback_false_trigger | FAIL |
| call-046 | callback_false_trigger | PASS |
| call-047 | callback_false_trigger | PASS |
| call-048 | callback_false_trigger | PASS |
| call-049 | callback_request_explicit | PASS |
| call-050 | callback_request_explicit | PASS |
| call-051 | callback_request_indirect | PASS |
| call-052 | callback_request_explicit | PASS |
| call-053 | callback_request_explicit | PASS |
| call-054 | callback_request_indirect | PASS |
| call-055 | callback_request_explicit | PASS |
| call-056 | callback_request_indirect | PASS |
| call-057 | callback_request_indirect | PASS |
| call-058 | callback_request_explicit | PASS |

## Aggregate metrics (docs/eval/Metrics.md)

- **Identification success rate**: no scored cases (target: ≥95% clean / ≥80% ambiguous)
- **Fails-safe rate**: no scored cases (target: 100%)
- **Retrieval recall@k**: no scored cases (target: ≥90%)
- **Tier-leakage rate**: no scored cases (target: 0%)
- **Callback recall**: 100% (n=10) — target: ≥90%
- **Callback precision**: 67% (n=15) — target: ≥95%
- **Phone extraction accuracy**: 100% (n=10) — target: no target yet
- **Callback false-trigger rate**: 42% (n=12) — target: no target yet
- **Hallucination rate**: not auto-scored in v1 (manual grading by design — see docs/eval/Metrics.md #5). Review the `out_of_scope_question` and `adversarial_tier_crossing` entries' answers below by hand.

## Per-entry detail

### call-037 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-038 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-039 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-040 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-041 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-042 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-043 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-044 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-045 (callback_false_trigger)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-046 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-047 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-048 (callback_false_trigger)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-049 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452508337",
  "phone_ok": true
}
```

### call-050 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452611984",
  "phone_ok": true
}
```

### call-051 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "+61 452 704 118",
  "phone_ok": true
}
```

### call-052 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0433 902 116",
  "phone_ok": true
}
```

### call-053 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452187660",
  "phone_ok": true
}
```

### call-054 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "(07) 3555 0192",
  "phone_ok": true
}
```

### call-055 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452349771",
  "phone_ok": true
}
```

### call-056 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0421 668 305",
  "phone_ok": true
}
```

### call-057 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0490 552 018",
  "phone_ok": true
}
```

### call-058 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 926 043",
  "phone_ok": true
}
```
