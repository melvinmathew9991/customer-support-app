# Rules — boundaries for AI-assisted work on this project

## 1. Libraries — use vs. avoid
**Use, and keep pinned to the exact versions in `pyproject.toml`** (bump
deliberately, not incidentally as a side effect of an unrelated change):
`langchain`, `langchain-community`, `langchain-ollama`, `langchain-openai`,
`langchain-chroma`, `langchain-text-splitters`, `chromadb`, `streamlit`,
`graphviz`, `python-dotenv`, `pydantic`/`pydantic-settings`.

**Avoid introducing:**
- A new LLM orchestration framework (LangGraph, LlamaIndex, CrewAI, etc.)
  alongside the existing hand-rolled `graph/` Node/Edge system — extend that
  system instead of bringing in a second, competing abstraction.
- A new heavy dependency (especially anything that pulls in `torch`, like
  raw HuggingFace `transformers`) as a hard dependency. `torch`-pulling
  packages (`openai-whisper`, `sentence-transformers`) must stay behind the
  existing optional extras (`audio`, `sentence-transformers`) — see the
  README's Windows `MAX_PATH` note for why.
- A second config system. All env/settings access goes through
  `config.py`'s `Settings`/`get_settings()` — never read `os.environ`
  directly in application code.
- A real database/ORM without discussing it first — `tools/user_info_db.py`
  is intentionally a mock; swapping it for something real is a scope
  decision, not a drive-by change.

## 2. Error handling approach
- Fail loudly and early on misconfiguration: e.g. `get_chat_model()` raises
  `RuntimeError` immediately if `llm_provider=openai` but no API key is set,
  rather than deferring to a confusing downstream failure. Follow this
  pattern for new provider/config branches.
- Retries belong in the graph's own vocabulary, not ad hoc `try/except`
  loops: use each `Edge`/`Node`'s existing `max_retries` /
  `RETRY_PROMPT` / `no_edges_found` mechanism when a step needs to
  re-prompt the user, instead of inventing a new retry pattern per node.
- Don't swallow exceptions silently. No bare `except: pass`. If an LLM/tool
  call can plausibly fail (bad structured output, DB miss, empty retrieval),
  surface it via the existing `no_edges_found`/edge-condition machinery so
  the conversation degrades to a retry prompt, not a stack trace or a
  silently wrong answer.
- Validate at the boundary: `pydantic` models (`domain/validation.py`) are
  the validation layer for anything coming out of an LLM (structured
  extraction) or a tool call. Don't add manual field-by-field validation
  that duplicates what a pydantic model already guarantees.

## 3. What the AI should do
- Follow the existing Node/Edge contracts (`graph/node.py`, `graph/edge.py`)
  for any new conversation state — a new stage in the flow should be a new
  `BaseNode`/`BaseEdge` subclass, wired into `pipeline.py`'s
  `_get_pipeline()`, not a special-cased branch elsewhere.
- Keep the free/paid knowledge-base split deterministic (chosen from
  `UserProfile.subscription`), never delegate "which KB to search" to the
  LLM.
- Add or update `tests/` for anything that doesn't require a live LLM
  (graph control flow, domain models, config) whenever behavior changes
  there. LLM-dependent behavior stays manually verified against Ollama, per
  the README, rather than mocked into false confidence.
- Keep `.env.example` in sync with any new `Settings` field, with a comment
  explaining default/purpose the way existing entries do.
- Match existing code style: no comments unless they explain a genuinely
  non-obvious constraint (see `config.py`'s `PROJECT_ROOT` and telemetry
  comments for the bar to clear); `ruff` clean at line-length 100.

## 4. What the AI should not do
- Don't hardcode API keys, model names tied to a paid tier, or any secret
  into source — everything provider/credential-related goes through `.env`
  / `Settings`.
- Don't commit `.env`, `chroma_db/`, or other generated/runtime artifacts
  (`.gitignore` already covers these — don't work around it).
- Don't let the LLM choose the free/paid retriever, decide authentication
  outcomes, or otherwise make a decision that should be deterministic
  business logic — that's the whole point of the graph architecture.
- Don't restructure `src/customer_support_app/` layout or rename the
  installable package without updating `pyproject.toml`
  (`[tool.setuptools.packages.find]`, `[project.scripts]`) and the README in
  the same change.
- Don't add UI/dashboard/auth features that aren't in `PRD.md`/`Phases.md`
  without flagging the scope change first.
