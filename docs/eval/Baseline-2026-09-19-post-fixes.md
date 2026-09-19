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
  "answer": "No, a free subscription doesn't allow you to sell in person.",
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
  "answer": "To get paid from your sales, you can use Shopify Payments, which allows you to receive payouts for credit card orders. When you use Shopify Payments, you can check your pay period to view when you receive payouts from credit card orders.",
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

### rag-free-003 (free_tier_question)
```json
{
  "answer": "You can find information about reporting copyright infringement on Shopify by referring to the FAQs below, specifically the section on \"Responding to a DMCA copyright notice\" and the section on \"Reporting copyright infringement\".",
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
  "answer": "The maximum number of locations that you can have depends on your plan.",
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
  "answer": "The maximum number of locations that you can have depends on your plan.",
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
  "answer": "Yes, you can accept manual payment methods like bank transfers or cash on delivery. When you set up a manual payment method, you can arrange to receive their payment in a way that works best for them. You can send an invoice to your customer, and after you receive the payment, you can manually approve the order.",
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
  "answer": "Yes, you can sell in person with your subscription. In fact, Shopify POS is designed to be used for in-person sales, and you can use it to sell almost anywhere, including brick-and-mortar stores, markets, and pop-up shops.",
  "sources": [
    "assets/paid/pos.txt",
    "assets/paid/pos.txt",
    "assets/paid/payments.txt",
    "assets/paid/locations.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-004 (paid_tier_question)
```json
{
  "answer": "According to the context, after you've captured the payment for an order placed using Shop Pay Installments, you'll receive full payment for your order within 1 to 3 business days, excluding the fee incurred for using Shop Pay Installments. You get paid by Affirm, and your payouts are sent to the same bank account that you use for Shopify Payments.",
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
  "answer": "Yes, you can set up multiple store locations in your Shopify store. You can use Shopify to track inventory and fulfill orders at multiple locations, and you can even split orders to fulfill from multiple locations if some of your inventory is out of stock at one location.",
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
  "answer": "Yes, you can manage multiple sales channels and locations together on your plan. Shopify allows you to set up multiple locations in your store, and you can also use Shopify POS to sell in person at different locations. Additionally, you can use Shopify's inventory management features to track and manage your products across multiple locations.",
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
  "answer": "Unfortunately, according to the context, manual payment methods like bank transfers or cash on delivery are not allowed on free subscription.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/pos.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-004 (adversarial_tier_crossing)
```json
{
  "answer": "Unfortunately, the provided context doesn't mention specific hardware requirements for selling in person at markets and pop-ups. It only mentions that you can connect Shopify with a range of retail hardware that helps you build your business, but it doesn't specify what hardware is required for in-person sales at markets and pop-ups.",
  "sources": [
    "assets/free/pos.txt",
    "assets/free/payments.txt",
    "assets/free/locations.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-oos-001 (out_of_scope_question)
```json
{
  "answer": "I don't have information on a return policy for damaged electronics. The context provided only discusses Shopify's copyright and trademark policies, as well as procedures for reporting infringement and responding to notices.",
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
  "answer": "I'm a customer support assistant, and I'm available to assist you with any questions or concerns you may have. However, I don't have a physical presence or a phone number that you can call to reach me directly.\n\nIf you have billing-related questions or concerns, I recommend reaching out to Shopify's customer support team through their official channels. You can contact them through their website, where you can submit a request for assistance or chat with a representative in real-time.\n\nAdditionally, you can also check Shopify's billing and payment FAQs, which may provide answers to your questions and help you resolve any issues you're experiencing.\n\nIf you're looking for more information on Shopify's customer support hours, you can check their website for their support hours and contact information.",
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
      "score": 0.9941
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
  "answer": "I couldn't find any information on the cost of the premium subscription in the provided context.",
  "retrieved_docs": [
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
    },
    {
      "source": "assets/free/pos.txt",
      "score": 1.1412
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
