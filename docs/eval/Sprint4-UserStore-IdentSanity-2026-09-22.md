# Eval run results

| id | category | result |
|---|---|---|
| ident-001 | happy_path_identification | PASS |
| ident-002 | happy_path_identification | PASS |
| ident-006 | happy_path_identification | PASS |
| ident-008 | happy_path_identification | PASS |
| ident-003 | ambiguous_identification | PASS |
| ident-007 | ambiguous_identification | PASS |
| ident-009 | ambiguous_identification | PASS |
| ident-010 | ambiguous_identification | PASS |
| ident-004 | unknown_user_identification | PASS |
| ident-011 | unknown_user_identification | PASS |
| ident-012 | unknown_user_identification | PASS |
| ident-005 | subscription_lookup_missing | PASS |
| ident-013 | subscription_lookup_missing | PASS |
| ident-014 | unknown_user_identification | PASS |

## Aggregate metrics (docs/eval/Metrics.md)

- **Identification success rate**: 100% (n=8) — target: ≥95% clean / ≥80% ambiguous
- **Fails-safe rate**: 100% (n=6) — target: 100%
- **Retrieval recall@k**: no scored cases (target: ≥90%)
- **Tier-leakage rate**: no scored cases (target: 0%)
- **Callback recall**: no scored cases (target: ≥90%)
- **Callback precision**: no scored cases (target: ≥95%)
- **Phone extraction accuracy**: no scored cases (target: no target yet)
- **Callback false-trigger rate**: no scored cases (target: no target yet)
- **Hallucination rate**: not auto-scored in v1 (manual grading by design — see docs/eval/Metrics.md #5). Review the `out_of_scope_question` and `adversarial_tier_crossing` entries' answers below by hand.

## Per-entry detail

### ident-001 (happy_path_identification)
```json
{
  "answer": "Hi, John Doe I am your Shopify Agent for today, you have the free subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-002 (happy_path_identification)
```json
{
  "answer": "Hi, Michael Jackson I am your Shopify Agent for today, you have the premium subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-006 (happy_path_identification)
```json
{
  "answer": "Hi, Carl Sagan I am your Shopify Agent for today, you have the premium subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-008 (happy_path_identification)
```json
{
  "answer": "Hi, John Doe I am your Shopify Agent for today, you have the free subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-003 (ambiguous_identification)
```json
{
  "answer": "Hi, Carl Sagan I am your Shopify Agent for today, you have the premium subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-007 (ambiguous_identification)
```json
{
  "answer": "Hi, Michael Jackson I am your Shopify Agent for today, you have the premium subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-009 (ambiguous_identification)
```json
{
  "answer": "Hi, Michael Jackson I am your Shopify Agent for today, you have the premium subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-010 (ambiguous_identification)
```json
{
  "answer": "Hi, John Doe I am your Shopify Agent for today, you have the free subscription I can help you with any Help or you can ask me to call you at anytime!",
  "name_ok": true,
  "subscription_ok": true,
  "node_ok": true
}
```

### ident-004 (unknown_user_identification)
```json
{
  "final_node": "GreetingNode"
}
```

### ident-011 (unknown_user_identification)
```json
{
  "final_node": "GreetingNode"
}
```

### ident-012 (unknown_user_identification)
```json
{
  "final_node": "GreetingNode"
}
```

### ident-005 (subscription_lookup_missing)
```json
{
  "final_node": "GreetingNode"
}
```

### ident-013 (subscription_lookup_missing)
```json
{
  "final_node": "GreetingNode"
}
```

### ident-014 (unknown_user_identification)
```json
{
  "final_node": "AuthenticatedUserNode",
  "said_after_fail_safe": [],
  "retrieval_ran": false
}
```
