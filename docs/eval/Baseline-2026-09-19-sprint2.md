# Eval run results

| id | category | result |
|---|---|---|
| ident-001 | happy_path_identification | PASS |
| ident-002 | happy_path_identification | PASS |
| ident-006 | happy_path_identification | PASS |
| ident-008 | happy_path_identification | PASS |
| ident-003 | ambiguous_identification | PASS |
| ident-007 | ambiguous_identification | MANUAL REVIEW |
| ident-009 | ambiguous_identification | PASS |
| ident-010 | ambiguous_identification | MANUAL REVIEW |
| ident-004 | unknown_user_identification | PASS |
| ident-011 | unknown_user_identification | PASS |
| ident-012 | unknown_user_identification | PASS |
| ident-005 | subscription_lookup_missing | PASS |
| ident-013 | subscription_lookup_missing | PASS |
| rag-free-001 | free_tier_question | PASS |
| rag-free-002 | free_tier_question | PASS |
| rag-free-003 | free_tier_question | PASS |
| rag-free-004 | free_tier_question | PASS |
| rag-paid-001 | paid_tier_question | PASS |
| rag-paid-002 | paid_tier_question | PASS |
| rag-paid-003 | paid_tier_question | PASS |
| rag-paid-004 | paid_tier_question | PASS |
| rag-adv-001 | adversarial_tier_crossing | PASS |
| rag-adv-002 | adversarial_tier_crossing | PASS |
| rag-adv-003 | adversarial_tier_crossing | PASS |
| rag-adv-004 | adversarial_tier_crossing | PASS |
| rag-oos-001 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-002 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-003 | out_of_scope_question | MANUAL REVIEW |
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

## Aggregate metrics (docs/eval/Metrics.md)

- **Identification success rate**: 100% (n=6) — target: ≥95% clean / ≥80% ambiguous
- **Fails-safe rate**: 100% (n=5) — target: 100%
- **Retrieval recall@k**: 100% (n=12) — target: ≥90%
- **Tier-leakage rate**: 0% (n=12) — target: 0%
- **Callback recall**: 100% (n=7) — target: ≥90%
- **Callback precision**: 100% (n=7) — target: ≥95%
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
  "answer": "I'm sorry, I didn't understand your response.\nPlease provide a full email address or phone number(in the format xxx-xxx-xxxx)",
  "final_node": "GreetingNode",
  "expected_behavior": "Genuinely uncertain by design - tools/user_info_db.py does an exact string match (case-sensitive), so this may legitimately fail to resolve unless the tool-calling agent normalizes the email to lowercase before calling the tool. Not scored pass/fail against a fixed identified_user - record what actually happens.",
  "note": "no fixed expected identity for this entry - manual review"
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
  "answer": "I'm sorry, I didn't understand your response.\nPlease provide a full email address or phone number(in the format xxx-xxx-xxxx)",
  "final_node": "GreetingNode",
  "expected_behavior": "Genuinely uncertain by design - tools/user_info_db.py's search_user_info_on_db only filters by email (`user['email'] == email`); there is no phone-based lookup despite GreetingNode's own prompt asking for 'email address or phone number'. Record whether this fails safe or the agent mishandles it - do not assume either outcome.",
  "note": "no fixed expected identity for this entry - manual review"
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

### rag-free-001 (free_tier_question)
```json
{
  "answer": "No, with a free subscription, you can only sell online.",
  "sources": [
    "assets/free/pos.txt",
    "assets/free/locations.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-free-002 (free_tier_question)
```json
{
  "answer": "You can be paid through Shopify Payments, which transfers funds to your bank account when a customer pays using Shopify Payments and specific accelerated checkouts. If you're using a third-party payment provider, payouts are sent to the same bank account used for Shopify Payments.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/pos.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-free-003 (free_tier_question)
```json
{
  "answer": "You can find information about reporting copyright infringement in the \"Reporting copyright infringement\" section of the help center.",
  "sources": [
    "assets/free/compliance.txt",
    "assets/free/compliance.txt",
    "assets/free/compliance.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-free-004 (free_tier_question)
```json
{
  "answer": "You can set up only a single location in your Shopify store on a free subscription.",
  "sources": [
    "assets/free/locations.txt",
    "assets/free/pos.txt",
    "assets/free/payments.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-001 (paid_tier_question)
```json
{
  "answer": "You can set up multiple locations in your Shopify store.",
  "sources": [
    "assets/paid/locations.txt",
    "assets/paid/pos.txt",
    "assets/paid/pos.txt",
    "assets/paid/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-002 (paid_tier_question)
```json
{
  "answer": "Yes, you can accept manual payment methods like bank transfers or cash on delivery, but you'll need to arrange to receive the payment in a way that works best for you.",
  "sources": [
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/pos.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-003 (paid_tier_question)
```json
{
  "answer": "Yes, you can sell in person with your subscription. You can use the basic features of the Shopify POS app to sell almost anywhere, including brick and mortar stores, markets, and pop-up shops.",
  "sources": [
    "assets/paid/pos.txt",
    "assets/paid/pos.txt",
    "assets/paid/locations.txt",
    "assets/paid/payments.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-004 (paid_tier_question)
```json
{
  "answer": "You receive full payment for your order within 1 to 3 business days, excluding the fee incurred for using Shop Pay Installments, after the payment is captured.",
  "sources": [
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/pos.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-001 (adversarial_tier_crossing)
```json
{
  "answer": "No, on a free subscription, you can set up only a single location in your Shopify store.",
  "sources": [
    "assets/free/locations.txt",
    "assets/free/pos.txt",
    "assets/free/compliance.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-002 (adversarial_tier_crossing)
```json
{
  "answer": "No, on a free subscription, you can only set up a single location in your Shopify store.",
  "sources": [
    "assets/free/locations.txt",
    "assets/free/pos.txt",
    "assets/free/compliance.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-003 (adversarial_tier_crossing)
```json
{
  "answer": "No, on a free subscription, manual payment methods like bank transfers or cash on delivery are not allowed.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/pos.txt",
    "assets/free/payments.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-004 (adversarial_tier_crossing)
```json
{
  "answer": "You don't need any Shopify POS hardware on a free subscription to sell in person, as in-person selling isn't available on this plan.",
  "sources": [
    "assets/free/pos.txt",
    "assets/free/payments.txt",
    "assets/free/compliance.txt",
    "assets/free/locations.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-oos-001 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/free/compliance.txt",
      "score": 0.8787
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 0.8799
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 0.9211
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 0.9213
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-002 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/free/payments.txt",
      "score": 0.9093
    },
    {
      "source": "assets/free/payments.txt",
      "score": 0.9284
    },
    {
      "source": "assets/free/payments.txt",
      "score": 0.9423
    },
    {
      "source": "assets/free/pos.txt",
      "score": 0.9705
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-003 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/free/pos.txt",
      "score": 0.9093
    },
    {
      "source": "assets/free/payments.txt",
      "score": 1.0001
    },
    {
      "source": "assets/free/payments.txt",
      "score": 1.1075
    },
    {
      "source": "assets/free/payments.txt",
      "score": 1.1404
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### call-001 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-004 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-005 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-006 (callback_request_explicit)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-002 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-007 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
}
```

### call-008 (callback_request_indirect)
```json
{
  "actually_fired": true,
  "final_node": "CallCustomerNode"
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
