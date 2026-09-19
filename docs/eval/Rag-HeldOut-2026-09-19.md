# Eval run results

| id | category | result |
|---|---|---|
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

## Aggregate metrics (docs/eval/Metrics.md)

- **Identification success rate**: no scored cases (target: ≥95% clean / ≥80% ambiguous)
- **Fails-safe rate**: no scored cases (target: 100%)
- **Retrieval recall@k**: 100% (n=16) — target: ≥90%
- **Tier-leakage rate**: 0% (n=16) — target: 0%
- **Callback recall**: no scored cases (target: ≥90%)
- **Callback precision**: no scored cases (target: ≥95%)
- **Hallucination rate**: not auto-scored in v1 (manual grading by design — see docs/eval/Metrics.md #5). Review the `out_of_scope_question` and `adversarial_tier_crossing` entries' answers below by hand.

## Per-entry detail

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
  "answer": "To update your bank account details, log in to your Shopify admin, go to Settings > Payments > Bank account, and click \"Edit\". Enter your new bank account details and save the changes.",
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
  "answer": "Yes, if you're using a payment provider other than Shopify Payments, you'll be charged a third-party transaction fee.",
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
  "answer": "Manual payment methods, such as money orders, are not allowed on a free subscription.",
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
  "answer": "No, with a free subscription, you can only accept manual payments outside of your online checkout, such as money orders or bank transfers.",
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
  "answer": "No, a free subscription doesn't allow selling in person, and since you mentioned running shops in two different cities, that implies in-person selling. Therefore, a free subscription cannot manage both shops.",
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
      "score": 1.0045
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
  "answer": "To cancel your subscription, go to your store's admin, click on \"Settings\" and then \"Account\". From there, click on \"Cancel Subscription\" and follow the prompts to confirm your cancellation.",
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
      "score": 0.8687
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
