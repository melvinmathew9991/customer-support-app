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
| rag-free-005 | free_tier_question | PASS |
| rag-free-006 | free_tier_question | PASS |
| rag-free-007 | free_tier_question | PASS |
| rag-free-008 | free_tier_question | PASS |
| rag-free-009 | free_tier_question | PASS |
| rag-free-010 | free_tier_question | PASS |
| rag-paid-005 | paid_tier_question | PASS |
| rag-paid-006 | paid_tier_question | PASS |
| rag-paid-007 | paid_tier_question | PASS |
| rag-paid-008 | paid_tier_question | PASS |
| rag-paid-009 | paid_tier_question | PASS |
| rag-paid-010 | paid_tier_question | PASS |
| rag-adv-005 | adversarial_tier_crossing | PASS |
| rag-adv-006 | adversarial_tier_crossing | PASS |
| rag-adv-007 | adversarial_tier_crossing | PASS |
| rag-adv-008 | adversarial_tier_crossing | PASS |
| rag-oos-004 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-005 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-006 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-007 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-008 | out_of_scope_question | MANUAL REVIEW |
| rag-free-011 | free_tier_question | PASS |
| rag-free-012 | free_tier_question | PASS |
| rag-free-013 | free_tier_question | PASS |
| rag-free-014 | free_tier_question | PASS |
| rag-paid-011 | paid_tier_question | PASS |
| rag-paid-012 | paid_tier_question | PASS |
| rag-oos-009 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-010 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-011 | out_of_scope_question | MANUAL REVIEW |
| rag-oos-012 | out_of_scope_question | MANUAL REVIEW |
| rag-adv-009 | adversarial_tier_crossing | PASS |
| rag-adv-010 | adversarial_tier_crossing | PASS |
| rag-adv-011 | adversarial_tier_crossing | PASS |
| rag-paid-013 | paid_tier_question | PASS |
| rag-paid-014 | paid_tier_question | PASS |
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

- **Identification success rate**: 100% (n=6) — target: ≥95% clean / ≥80% ambiguous
- **Fails-safe rate**: 100% (n=5) — target: 100%
- **Retrieval recall@k**: 100% (n=39) — target: ≥90%
- **Tier-leakage rate**: 0% (n=39) — target: 0%
- **Callback recall**: 96% (n=27) — target: ≥90%
- **Callback precision**: 90% (n=29) — target: ≥95%
- **Phone extraction accuracy**: 100% (n=26) — target: no target yet
- **Callback false-trigger rate**: 14% (n=21) — target: no target yet
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
  "answer": "You receive payments through Shopify Payouts when a customer pays using Shopify Payments and specific accelerated checkouts.",
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
  "answer": "You can find information about reporting copyright infringement in the \"Reporting copyright infringement\" section of our help center.",
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
  "answer": "Yes, you can accept manual payment methods like bank transfers or cash on delivery.",
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
  "answer": "Yes, you can use Shopify POS to sell in person with your subscription.",
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
  "answer": "You receive full payment for your order within 1 to 3 business days, excluding the fee incurred for using Shop Pay Installments.",
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
  "answer": "No, you cannot set up multiple store locations on a free subscription.",
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
  "answer": "Manual payment methods, such as money orders or bank transfers, are not allowed on a free subscription.",
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
      "score": 0.9342
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
      "score": 1.0802
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
  "extracted_phone": "0452444333",
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
  "extracted_phone": "0452 222 111",
  "phone_ok": true
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

### rag-free-005 (free_tier_question)
```json
{
  "answer": "Yes, it's normal for it to take a few days after a payout is sent for the funds to be deposited into your bank account.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-free-006 (free_tier_question)
```json
{
  "answer": "You can update the information in your Shopify Payments settings.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-free-007 (free_tier_question)
```json
{
  "answer": "Yes, you are charged a third-party transaction fee if you use a payment provider other than Shopify Payments.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/compliance.txt",
    "assets/free/pos.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-free-008 (free_tier_question)
```json
{
  "answer": "A copyright protects tangible original works, like photos or text descriptions on an online store, whereas a trademark is a symbol or word that identifies and distinguishes a business or product from others, and trade dress covers the image or appearance of a product, including features such as size, shape, color and texture.",
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

### rag-free-009 (free_tier_question)
```json
{
  "answer": "You have two days to respond to a trademark notice before the content is removed from your store.",
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

### rag-free-010 (free_tier_question)
```json
{
  "answer": "To file a DMCA counter notice, you must include the following information: \n\n1. The legal name and sufficient contact information of the person submitting the counter notice.\n2. Identification of the content that has been removed and the original location of the content before it was removed.\n3. A statement under penalty of perjury that you have a good faith belief that the content was removed as a result of a mistake or misidentification.\n4. A statement that you consent to the jurisdiction of Federal District Court for the judicial district in which your address is located or, if your address is located outside of the United States, you consent to jurisdiction of the Federal District Court for the District of Delaware, and a statement that you accept service of process from the party who submitted the copyright notice or its agent.\n5. Your physical or electronic signature.",
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

### rag-paid-005 (paid_tier_question)
```json
{
  "answer": "Yes, if your store and your customers are based in Canada, you can accept email money transfers as a manual payment method.",
  "sources": [
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-006 (paid_tier_question)
```json
{
  "answer": "You can accept common types of manual payments such as cash on delivery (COD), money orders, and bank transfers.",
  "sources": [
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-007 (paid_tier_question)
```json
{
  "answer": "No, Shopify POS is available for iOS and Android devices only.",
  "sources": [
    "assets/paid/pos.txt",
    "assets/paid/pos.txt",
    "assets/paid/compliance.txt",
    "assets/paid/locations.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-008 (paid_tier_question)
```json
{
  "answer": "Locations that you deactivate do not count toward your location limit.",
  "sources": [
    "assets/paid/locations.txt",
    "assets/paid/compliance.txt",
    "assets/paid/compliance.txt",
    "assets/paid/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-009 (paid_tier_question)
```json
{
  "answer": "If Shopify receives several notices of alleged copyright infringement that are not countered by the store, Shopify may terminate the store.",
  "sources": [
    "assets/paid/compliance.txt",
    "assets/paid/compliance.txt",
    "assets/paid/compliance.txt",
    "assets/paid/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-paid-010 (paid_tier_question)
```json
{
  "answer": "No, you won't be charged third-party transaction fees when you use Shopify Payments.",
  "sources": [
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/compliance.txt",
    "assets/paid/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-005 (adversarial_tier_crossing)
```json
{
  "answer": "Manual payments outside of your online checkout, such as money orders or bank transfers, are not allowed on a free subscription.",
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

### rag-adv-006 (adversarial_tier_crossing)
```json
{
  "answer": "No, on a free subscription, manual payments outside of your online checkout, such as money orders or bank transfers, are not allowed.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/compliance.txt",
    "assets/free/pos.txt",
    "assets/free/payments.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-007 (adversarial_tier_crossing)
```json
{
  "answer": "No, a free subscription doesn't allow selling in person, and since you mentioned running shops in two different cities, this implies in-person selling. Therefore, a free subscription cannot manage both shops.",
  "sources": [
    "assets/free/locations.txt",
    "assets/free/compliance.txt",
    "assets/free/pos.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-008 (adversarial_tier_crossing)
```json
{
  "answer": "You are not restricted to selling online only on your plan. You can use Shopify POS to sell your products in person in retail stores, popups, and other locations.",
  "sources": [
    "assets/paid/pos.txt",
    "assets/paid/pos.txt",
    "assets/paid/compliance.txt",
    "assets/paid/payments.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-oos-004 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/free/payments.txt",
      "score": 1.0124
    },
    {
      "source": "assets/free/payments.txt",
      "score": 1.0194
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 1.0357
    },
    {
      "source": "assets/free/payments.txt",
      "score": 1.0584
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-005 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/paid/pos.txt",
      "score": 0.785
    },
    {
      "source": "assets/paid/pos.txt",
      "score": 0.8267
    },
    {
      "source": "assets/paid/compliance.txt",
      "score": 0.9211
    },
    {
      "source": "assets/paid/compliance.txt",
      "score": 0.9322
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-006 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/free/compliance.txt",
      "score": 0.9657
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 0.9953
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 1.0113
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 1.0114
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-007 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/paid/compliance.txt",
      "score": 0.9594
    },
    {
      "source": "assets/paid/payments.txt",
      "score": 0.9729
    },
    {
      "source": "assets/paid/payments.txt",
      "score": 0.9839
    },
    {
      "source": "assets/paid/compliance.txt",
      "score": 1.0235
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-008 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/free/payments.txt",
      "score": 0.6251
    },
    {
      "source": "assets/free/payments.txt",
      "score": 0.8162
    },
    {
      "source": "assets/free/payments.txt",
      "score": 0.8713
    },
    {
      "source": "assets/free/pos.txt",
      "score": 1.0679
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-free-011 (free_tier_question)
```json
{
  "answer": "If you use Shopify Payments, you can check your pay period to view when you receive payouts from credit card orders.",
  "sources": [
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-free-012 (free_tier_question)
```json
{
  "answer": "You can submit a copyright infringement notice to Shopify through their online form in your store admin.",
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

### rag-free-013 (free_tier_question)
```json
{
  "answer": "You can send a counter notice to us through a form in your store admin.",
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

### rag-free-014 (free_tier_question)
```json
{
  "answer": "You can send your response to us through your store admin. Your response must have all of the following information to be considered: the legal name and sufficient contact information of the person submitting the response, identification of the content that has been removed and the original location of the content before it was removed, a statement under penalty of perjury that you have a good faith belief that the content was removed as a result of a mistake or misidentification, a statement that you consent to the jurisdiction of Federal District Court for the judicial district in which your address is located or, if your address is located outside of the United States, you consent to jurisdiction of the Federal District Court for the District of Delaware, and a statement that you accept service of process from the party who submitted the trademark or trade dress notice or its agent.",
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

### rag-paid-011 (paid_tier_question)
```json
{
  "answer": "To set up a manual payment method, you can arrange to receive your customer's payment in a way that works best for them, such as sending an invoice to your customer. After you receive the payment, you can then manually approve the order.",
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

### rag-paid-012 (paid_tier_question)
```json
{
  "answer": "I don't have information about that in our help center.",
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

### rag-oos-009 (out_of_scope_question)
```json
{
  "answer": "You can enable Shopify Payments in the Payment providers area of your Shopify admin.",
  "retrieved_docs": [
    {
      "source": "assets/free/payments.txt",
      "score": 0.4416
    },
    {
      "source": "assets/free/payments.txt",
      "score": 0.5679
    },
    {
      "source": "assets/free/pos.txt",
      "score": 0.6858
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 0.7717
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-010 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/free/locations.txt",
      "score": 0.8085
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 0.8869
    },
    {
      "source": "assets/free/compliance.txt",
      "score": 0.8876
    },
    {
      "source": "assets/free/pos.txt",
      "score": 0.8882
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-011 (out_of_scope_question)
```json
{
  "answer": "To connect a card reader to Shopify POS, you'll need to set up your card reader in the Shopify POS app and link it to your Shopify admin. This will allow you to process payments and sync orders with your online store.",
  "retrieved_docs": [
    {
      "source": "assets/paid/pos.txt",
      "score": 0.5678
    },
    {
      "source": "assets/paid/pos.txt",
      "score": 0.6067
    },
    {
      "source": "assets/paid/payments.txt",
      "score": 0.7455
    },
    {
      "source": "assets/paid/payments.txt",
      "score": 0.8657
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-oos-012 (out_of_scope_question)
```json
{
  "answer": "I don't have information about that in our help center.",
  "retrieved_docs": [
    {
      "source": "assets/paid/compliance.txt",
      "score": 1.0447
    },
    {
      "source": "assets/paid/compliance.txt",
      "score": 1.0988
    },
    {
      "source": "assets/paid/compliance.txt",
      "score": 1.1091
    },
    {
      "source": "assets/paid/compliance.txt",
      "score": 1.1232
    }
  ],
  "actually_fired": false,
  "final_node": "AuthenticatedUserNode",
  "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5"
}
```

### rag-adv-009 (adversarial_tier_crossing)
```json
{
  "answer": "Manual payments outside of your online checkout, such as money orders or bank transfers, are not allowed on a free subscription.",
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

### rag-adv-010 (adversarial_tier_crossing)
```json
{
  "answer": "No, cash on delivery is not available on a free subscription.",
  "sources": [
    "assets/free/pos.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt",
    "assets/free/payments.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
}
```

### rag-adv-011 (adversarial_tier_crossing)
```json
{
  "answer": "Manual payments outside of your online checkout, such as money orders, are not allowed on a free subscription.",
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

### rag-paid-013 (paid_tier_question)
```json
{
  "answer": "Yes, you can accept manual payments outside of your online checkout, such as money orders or bank transfers.",
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

### rag-paid-014 (paid_tier_question)
```json
{
  "answer": "When a customer pays for their order using a manual payment method like bank transfer, you can manually approve the order after receiving the payment.",
  "sources": [
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/payments.txt",
    "assets/paid/compliance.txt"
  ],
  "recall_hit": true,
  "tier_leak": false
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
  "extracted_phone": "0452615220",
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
