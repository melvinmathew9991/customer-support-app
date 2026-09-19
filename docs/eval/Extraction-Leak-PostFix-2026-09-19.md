# Eval run results

| id | category | result |
|---|---|---|
| call-007 | callback_request_indirect | PASS |
| call-027 | callback_request_explicit | PASS |
| call-028 | callback_request_explicit | PASS |
| call-029 | callback_request_explicit | PASS |
| call-030 | callback_request_indirect | PASS |
| call-031 | callback_request_indirect | PASS |
| call-032 | callback_request_explicit | PASS |
| call-033 | callback_request_explicit | FAIL |
| call-034 | callback_request_indirect | PASS |
| call-035 | callback_request_explicit | PASS |
| call-036 | callback_request_explicit | PASS |

## Aggregate metrics (docs/eval/Metrics.md)

- **Identification success rate**: no scored cases (target: ≥95% clean / ≥80% ambiguous)
- **Fails-safe rate**: no scored cases (target: 100%)
- **Retrieval recall@k**: no scored cases (target: ≥90%)
- **Tier-leakage rate**: no scored cases (target: 0%)
- **Callback recall**: 91% (n=11) — target: ≥90%
- **Callback precision**: 100% (n=10) — target: ≥95%
- **Phone extraction accuracy**: 100% (n=10) — target: no target yet
- **Callback false-trigger rate**: no scored cases (target: no target yet)
- **Hallucination rate**: not auto-scored in v1 (manual grading by design — see docs/eval/Metrics.md #5). Review the `out_of_scope_question` and `adversarial_tier_crossing` entries' answers below by hand.

## Per-entry detail

### call-007 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 222 111",
  "phone_ok": true
}
```

### call-027 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 810 274",
  "phone_ok": true
}
```

### call-028 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0433 690 512",
  "phone_ok": true
}
```

### call-029 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "(03) 9555 0177",
  "phone_ok": true
}
```

### call-030 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0490 128 345",
  "phone_ok": true
}
```

### call-031 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0421 907 366",
  "phone_ok": true
}
```

### call-032 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "+44 7700 900 461",
  "phone_ok": true
}
```

### call-033 (callback_request_explicit)
```json
{
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode"
}
```

### call-034 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0466 253 018",
  "phone_ok": true
}
```

### call-035 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 333 667",
  "phone_ok": true
}
```

### call-036 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode",
  "extracted_phone": "0452 333 668",
  "phone_ok": true
}
```
