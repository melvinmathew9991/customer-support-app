# Eval run results

| id | category | result |
|---|---|---|
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

## Aggregate metrics (docs/eval/Metrics.md)

- **Identification success rate**: no scored cases (target: ≥95% clean / ≥80% ambiguous)
- **Fails-safe rate**: no scored cases (target: 100%)
- **Retrieval recall@k**: 100% (n=11) — target: ≥90%
- **Tier-leakage rate**: 0% (n=11) — target: 0%
- **Callback recall**: no scored cases (target: ≥90%)
- **Callback precision**: no scored cases (target: ≥95%)
- **Hallucination rate**: not auto-scored in v1 (manual grading by design — see docs/eval/Metrics.md #5). Review the `out_of_scope_question` and `adversarial_tier_crossing` entries' answers below by hand.

## Per-entry detail

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
  "answer": "You can send a counter notice to us through a form in your store admin. Your counter notice must have all of the following information to be considered: the legal name and sufficient contact information of the person submitting the counter notice, identification of the content that has been removed and the original location of the content before it was removed, a statement under penalty of perjury that you have a good faith belief that the content was removed as a result of a mistake or misidentification, a statement that you consent to the jurisdiction of Federal District Court for the judicial district in which your address is located or, if your address is located outside of the United States, you consent to jurisdiction of the Federal District Court for the District of Delaware, and a statement that you accept service of process from the party who submitted the copyright notice or its agent, and your physical or electronic signature.",
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
  "answer": "To set up a manual payment method, you can arrange to receive your customer's payment in a way that works best for them. You can send an invoice to your customer, and after you receive the payment, you can manually approve the order.",
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
  "answer": "To add a location to your POS device, you can use the Shopify POS app. When you make sales from physical locations using the Shopify POS app, then you can add a location to your sales device to track your inventory accurately.",
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
  "answer": "To enable Shopify Payments, go to your Shopify admin, navigate to Settings > Payments, and click on \"Add payment provider\". Select Shopify Payments from the list of available payment providers, and follow the prompts to set up your payment information.",
  "retrieved_docs": [
    {
      "source": "assets/free/payments.txt",
      "score": 0.4438
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
  "answer": "To add a new product to your store, go to the \"Products\" section in your Shopify admin, click \"Add product\", and follow the prompts to enter the product details.",
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
  "answer": "To connect a card reader to Shopify POS, you'll need to purchase a supported card reader and connect it to your Shopify POS app. You can find a list of supported card readers in the Hardware section.",
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
  "answer": "You can reset your admin password by following these steps:\n\n1. Go to your store's admin panel.\n2. Click on \"Account\" in the top right corner of the screen.\n3. Click on \"Change Password\".\n4. Enter your current password and a new password.\n5. Click \"Save Changes\".\n\nAlternatively, you can also reset your password by following the instructions in the \"Forgot Password\" link on the login page.",
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
  "answer": "Yes, you can accept manual payments outside of your online checkout, such as money orders or bank transfers, on your free subscription plan.",
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
  "answer": "No, cash on delivery is not available on your plan.",
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
  "answer": "Yes, you can accept manual payments outside of your online checkout, such as money orders or bank transfers, but you'll be charged third-party transaction fees for all orders that aren't brokered financially by Shopify.",
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
