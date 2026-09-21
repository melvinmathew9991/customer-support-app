# PRD — Customer Support App

## 1. What we're building
A LangChain-based conversational support agent for an e-commerce (Shopify-style)
storefront. Instead of one freeform chat agent, the conversation is modeled as a
deterministic graph of `Node`s and `Edge`s, so what the bot is allowed to do at
each stage of the conversation is constrained and predictable rather than left
entirely to the LLM's judgment.

Conversation flow:

```
GreetingNode → (identify user via tools) → AuthenticatedUserNode → (call-me request?) → CallCustomerNode
```

Runs fully locally by default via Ollama (no API key required); OpenAI is
available as an opt-in swap via `.env`.

## 2. Problem it solves
Storefronts get a high volume of repetitive support questions (payments,
locations, POS, compliance) that don't need a human, plus occasional requests
that genuinely do (a customer asking to be called back). A plain RAG chatbot
either answers everything with the same knowledge base regardless of who's
asking, or hands off to a human too eagerly. This app:
- Identifies the customer first (email/phone → DB lookup) before answering
  anything support-related. If identification still fails after the retries,
  the bot says it could not verify the account and the conversation ends; the
  user starts a new one. An unidentified user is never answered from any KB.
- Answers from a knowledge base scoped to that customer's own subscription
  tier (free vs. paid), so premium content never leaks to free users and
  free users aren't given irrelevant premium answers.
- Detects when a user actually wants a phone callback and routes that to a
  distinct ticket-creation flow instead of trying to resolve it via RAG.

## 3. Target users
- **End customers** of the storefront, chatting via the Streamlit widget (or
  CLI, for local testing) to get help with payments, POS, locations, or
  compliance questions, or to request a callback.
- **The store's support/eng team**, who own the knowledge base content
  (`assets/free/`, `assets/paid/`) and the user database, and who need the
  bot's behavior to be predictable and auditable (hence the explicit graph
  instead of a single opaque agent).
- **Developers extending the app**, who need the conversation flow to be
  legible enough to add new nodes/edges without destabilizing existing ones.

## 4. Core features
1. **Identification** — greets the user, asks for email or phone number,
   looks them up via a tool-calling agent (`tools/user_info_db.py`), and
   extracts a structured `UserProfile` (name, subscription tier).
2. **Tiered RAG support answers** — `AuthenticatedUserNode` answers free-text
   questions using a Chroma vector store built from `assets/free` or
   `assets/paid`, chosen deterministically by the user's own subscription
   (never left to the LLM to pick).
3. **Call-me detection & ticketing** — detects a callback request in natural
   language, extracts the phone number, and routes to `CallCustomerNode`,
   which can transcribe a call via Whisper (optional extra) and produces a
   ticket summary for the user.
4. **Graph visualization** — a "Graph" tab in the Streamlit UI renders the
   current conversation's Node/Edge DAG via Graphviz, so the state machine
   is inspectable while chatting.
5. **Local-first / provider-agnostic LLM & embeddings** — Ollama by default
   (no API key), OpenAI as an opt-in via `.env`, without changing any
   application code.

## 5. Non-goals (for now)
- No persistent chat history across process restarts (state lives in the
  Streamlit session / in-memory pipeline only).
- No real user authentication (email/phone lookup is identification against
  a mock DB, not a login system with passwords/sessions).
- No multi-turn negotiation of subscription tier or account changes — the
  bot reads the tier, it doesn't manage it.
- No production telemetry/analytics dashboard.

## 6. Success criteria
- A user can complete the full flow (greeting → identification → tiered RAG
  answer → optional callback ticket) against a local Ollama model with no
  API key.
- Free-tier users never receive paid-tier knowledge-base content and vice
  versa.
- `pytest` (deterministic graph/config/domain tests) passes without Ollama
  or network access.
- Switching `LLM_PROVIDER`/`EMBEDDINGS_PROVIDER` in `.env` is the only
  change needed to move between Ollama and OpenAI.
