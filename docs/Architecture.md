# Architecture — Customer Support App

## 1. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Orchestration | LangChain 0.3.7 (+ `langchain-community`, `langchain-text-splitters`) | Pinned exact versions in `pyproject.toml`. |
| LLM (default) | Ollama via `langchain-ollama` 0.2.0 | `llama3.2:3b` by default; any tool-calling-capable model works. |
| LLM (opt-in) | OpenAI via `langchain-openai` 0.2.6 | Set `LLM_PROVIDER=openai` + `OPENAI_API_KEY`. |
| Embeddings | Ollama (`nomic-embed-text`) by default; `sentence-transformers` optional | Ollama avoids pulling `torch`. |
| Vector store | Chroma via `langchain-chroma` 0.1.4 / `chromadb` 0.5.20 | One collection per subscription tier (free/paid). |
| Config/validation | `pydantic` 2.9.2 + `pydantic-settings` 2.6.1 | `Settings` in `config.py`, `.env`-driven. |
| Web UI | Streamlit 1.39.0 | `app.py`; two tabs: Chat, Graph. |
| Graph rendering | `graphviz` 0.20.3 | Renders the live Node/Edge DAG in the Graph tab. |
| CLI | stdlib + console script | `customer-support-chat` entry point (`cli.py`). |
| Audio (optional) | `openai-whisper`, `librosa`, `numexpr` | Only under the `audio` extra; transcribes call-me requests. |
| Tests | `pytest` 8.3.3, `pytest-mock` | Cover graph framework, domain, config — no LLM calls. |
| Lint | `ruff` 0.7.4 | line-length 100, rules `E`, `F`, `I`. |

## 2. Conversation flow

```
GreetingNode
   │  (user gives email/phone)
   ▼
UserInfoChainBasedEdge  ── tool-calling agent: user_info_db_search → user_subscription_db_search
   │  produces UserProfile (name, subscription)
   │  (after its retries run out it hands over an error instead: the node says it could not
   │   verify the account and the conversation ends, #37)
   ▼
AuthenticatedUserNode (RetrievalNode)
   │  RAG over Chroma: free or paid collection, chosen from UserProfile.subscription
   │
   ├─ normal question → answered directly, stays on this node
   │
   └─ CallCustomerEdge detects "please call me" intent, extracts phone number
          ▼
      CallCustomerNode (MultifunctionNode, final_state=True)
          transcribes/produces a PhoneCallTicket, replies with a ticket summary, ends the conversation
```

This is implemented as an explicit DAG (`src/customer_support_app/graph/`)
rather than a single agent loop, so each state's allowed inputs/outputs and
retry behavior (`RETRY_PROMPT`, `no_edges_found`) are declared, not implicit
in prompt engineering.

## 3. Request lifecycle (`CustomerSupportPipeline.run`)

1. `pipeline.py` holds `_current_node` and a `MessageHistory`.
2. On the first call (`_current_node is None`), it builds the graph
   (`_get_pipeline`) and emits the current node's `greeting_message()`.
3. On each subsequent call, it appends the user's message to history, calls
   `_current_node.execute(history)`, and:
   - if the node/edge returns an `EdgeOutput`, records any `message_output`s
     and, if a `next_node` is set, transitions to it and emits its greeting;
   - if it returns a plain `MessageOutput`, records and returns it directly.
4. Returns `(assistant_messages, is_over)` to the caller (`app.py` or
   `cli.py`), which is responsible for I/O and persisting nothing beyond the
   process's own memory.

State (`MessageHistory`, `_current_node`) lives only in the
`CustomerSupportPipeline` instance — in Streamlit that's `st.session_state`,
so it resets when the session ends; there is no database-backed session
store.

## 4. Folder structure

```
customer_support_app/
├── pyproject.toml               # single source of truth for deps/metadata
├── .env.example                 # copy to .env; Ollama-by-default settings
├── assets/
│   ├── free/                    # free-tier KB docs (payments.txt, locations.txt, pos.txt, compliance.txt)
│   ├── paid/                    # paid-tier KB docs (same topics, deeper content)
│   └── audio/                   # sample call audio for the transcription tool
├── docs/                        # this file + PRD/Rules/Phases/Design/Sprints
├── notebooks/                   # legacy exploratory prototype (customer_support.ipynb) — not the source of truth
├── src/customer_support_app/    # the installable package
│   ├── config.py                 # Settings (pydantic-settings): provider selection, paths
│   ├── logging_config.py
│   ├── pipeline.py                # CustomerSupportPipeline: builds the graph, drives execute()
│   ├── cli.py                     # terminal chat entrypoint (customer-support-chat)
│   ├── app.py                     # Streamlit entrypoint (Chat + Graph tabs)
│   ├── agents/support.py          # concrete Nodes/Edges for this conversation (Greeting, AuthenticatedUser, CallCustomer)
│   ├── domain/
│   │   ├── chat.py                 # MessageHistory, Role
│   │   ├── graph.py                 # MessageOutput, EdgeOutput
│   │   └── validation.py            # UserProfile, PhoneCallRequest, PhoneCallTicket (pydantic)
│   ├── graph/                      # reusable Node/Edge DAG framework (provider-agnostic)
│   │   ├── node.py, edge.py          # BaseNode/BaseEdge contracts
│   │   ├── chain_based_node.py       # RetrievalNode, MultifunctionNode (tool/RAG-backed nodes)
│   │   ├── chain_based_edge.py       # ZeroShotChainBasedEdge (tool-calling agent as an edge)
│   │   ├── text_based_edge.py        # PydanticTextBasedEdge (structured-extraction-gated edge)
│   │   └── static_text_node.py
│   ├── tools/
│   │   ├── user_store.py             # UserStore: MockUserStore + SqliteUserStore (real, auto-seeded)
│   │   ├── rag_responder.py          # HelpCenterAgent: builds/queries free & paid Chroma retrievers; reindex + staleness check
│   │   └── audio_transcribe.py       # Whisper-based call transcription (optional `audio` extra)
│   └── ui/graph_renderer.py         # renders the DAG in the Streamlit "Graph" tab
├── scripts/reindex_kb.py          # rebuild the Chroma indexes from assets/ (see README "Updating the knowledge base")
└── tests/                         # pytest: agents/, graph/, domain/, tools/, test_config.py — no Ollama/network required
```

## 5. Configuration

All settings are environment-driven via `Settings` (`config.py`,
`pydantic-settings`), loaded from `.env` at `PROJECT_ROOT`. Key knobs:
`LLM_PROVIDER`, `OLLAMA_MODEL`/`OLLAMA_BASE_URL`, `OPENAI_MODEL`/
`OPENAI_API_KEY`, `EMBEDDINGS_PROVIDER`, `OLLAMA_EMBED_MODEL`,
`SENTENCE_TRANSFORMER_MODEL`, `ASSETS_DIR`, `CHROMA_DIR`, `AGENT_VERBOSE`,
`LOG_LEVEL`, `SESSION_DB_PATH`, `USER_STORE_PROVIDER`/`USER_STORE_DB_PATH`.
`PROJECT_ROOT` is derived from `config.py`'s own location, not the process
CWD, so behavior is the same whether run via Streamlit, the CLI, or an IDE.

## 6. Known architectural limitations (current state)
- The user store (`tools/user_store.py`, `SqliteUserStore` by default since Sprint 4) is a
  real, persistent lookup, but it's still a lookup, not authentication: anyone who knows a
  customer's email or phone number is served that customer's tier
  (`docs/User-Store-Design.md` decision 2, a stated non-goal in `PRD.md`).
- LLM-dependent behavior (tool-calling, RAG answers, structured extraction)
  is not covered by the automated test suite — it's exercised manually
  against a live Ollama server, since it's slow and non-deterministic.
