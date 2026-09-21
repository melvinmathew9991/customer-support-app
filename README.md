# customer-support-app

A LangChain, graph-orchestrated LLM customer support agent. Conversation
state is modeled as a DAG of `Node`s and `Edge`s (see `src/customer_support_app/graph/`)
instead of one freeform agent, so behavior at each stage of the conversation
is constrained and predictable:

```
GreetingNode → (identify user via tools) → AuthenticatedUserNode → (call-me request?) → CallCustomerNode
```

- **GreetingNode** asks for an email/phone number.
- A tool-calling agent looks the user up (`tools/user_info_db.py`) and
  extracts a structured `UserProfile`.
- **AuthenticatedUserNode** answers support questions via RAG (Chroma +
  local embeddings) over `assets/free` or `assets/paid`, chosen
  deterministically by the user's own subscription tier.
- A **call-me** request is detected and routed to **CallCustomerNode**,
  which (optionally) transcribes a call via Whisper and produces a ticket.

Runs **fully locally by default** via [Ollama](https://ollama.com/) - no API
key required. OpenAI is available as an opt-in via `.env`.

## Project layout

```
customer_support_app/
├── pyproject.toml            # single source of truth for deps/metadata
├── .env.example
├── assets/                   # knowledge base docs + sample call audio (runtime data)
├── docs/                     # design docs (PRD, Architecture, Rules, Phases, Design, Persistence-Design, Sprints, Process-Evaluation)
├── notebooks/                # legacy exploratory prototype (customer_support.ipynb)
├── src/customer_support_app/ # the installable package
│   ├── config.py             # pydantic-settings: LLM/embeddings provider, paths
│   ├── logging_config.py
│   ├── pipeline.py           # CustomerSupportPipeline
│   ├── cli.py                # terminal chat entrypoint
│   ├── app.py                # Streamlit entrypoint
│   ├── agents/support.py     # the concrete nodes/edges for this conversation
│   ├── domain/                # dataclasses/pydantic models (chat, graph, validation)
│   ├── graph/                 # the reusable Node/Edge DAG framework
│   ├── tools/                 # user DB lookup, RAG retriever, call transcription
│   └── ui/graph_renderer.py   # renders the DAG in the Streamlit "Graph" tab
└── tests/                     # pytest unit tests (no Ollama required)
```

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate       Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
```

Optional extras:
- `pip install -e ".[audio]"` - enables the phone-call transcription tool
  (`tools/audio_transcribe.py`); pulls in `torch`/Whisper (see Windows note
  below). With it, a callback request transcribes a sample call and opens a
  ticket with its summary. Without the extra, a callback is logged and the
  conversation ends normally. If the model returns a ticket that cannot be
  read, the callback is logged the same way instead of failing (#43).
- `pip install -e ".[sentence-transformers]"` - alternative local embeddings
  backend; also pulls in `torch`.

## Running locally with Ollama (default, no API key needed)

1. Install Ollama and pull a tool-calling capable chat model plus an
   embedding model:

   ```
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```

2. Make sure the Ollama server is running (it starts automatically on
   install, or run `ollama serve`).
3. Copy `.env.example` to `.env`. The defaults already point at Ollama:

   ```
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3.2:3b
   OLLAMA_BASE_URL=http://localhost:11434
   EMBEDDINGS_PROVIDER=ollama
   OLLAMA_EMBED_MODEL=nomic-embed-text
   ```

Any Ollama model that supports tool/function calling can be used (e.g.
`llama3.2`, `llama3.1`, `qwen2.5`, `mistral-nemo`) - set `OLLAMA_MODEL`
accordingly. The 3B model above is the one this project is tuned and measured
against. A larger model is **not** automatically better here: `llama3.1:8b` was
tested on the full golden set and was worse (it writes its second tool call as
text, which broke identification, and it answers "no" to every callback check);
see `docs/eval/Model-Experiment-Results-2026-09-20.md`. Re-run the golden set
(`tests/eval/run_eval.py`) before switching models.

### Switching to OpenAI instead

Set the following in `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
```

`EMBEDDINGS_PROVIDER` can stay `ollama`, or be set to `sentence-transformers`
to embed locally via HuggingFace instead (pulls in `torch` - see the Windows
note below).

### Windows note: long paths

`torch` (used by the optional `audio` and `sentence-transformers` extras)
ships very long header file paths. If your project/venv path is deeply
nested (e.g. under OneDrive), installing it can fail with a
`No such file or directory` `OSError` due to Windows' default 260-character
`MAX_PATH` limit. Either enable Windows long path support
(https://pip.pypa.io/warnings/enable-long-paths), or keep the venv on a
short path, e.g. `py -3.10 -m venv C:\venvs\customer-support`. The default
configuration (`EMBEDDINGS_PROVIDER=ollama`, no `audio` extra) avoids this
entirely.

`pip install -e ".[audio]"` works in a fresh venv as it is. The extra pins
`openai-whisper==20250625` because every release up to `20240930` builds from source
with a `setup.py` that imports `pkg_resources`, which current `setuptools` no longer
ships, so installing one of those fails with `No module named 'pkg_resources'` (#44).

## Running the app

```bash
streamlit run src/customer_support_app/app.py
```

Or a terminal chat (installed as a console script):

```bash
customer-support-chat
```

Type `quit` or `exit` to leave, or press Ctrl+D (Ctrl+Z then Enter on Windows). Piped
input that runs out ends the session the same way, with exit code 0.

### Saved conversations

A conversation is saved after every turn, so it survives closing the app or restarting the
server. It goes into a local SQLite file (`data/sessions.sqlite` by default, set
`SESSION_DB_PATH` to move it), which holds names, emails and phone numbers in the clear and
is gitignored.

- **Terminal:** a bare run starts a new conversation and prints its id.
  `customer-support-chat --session <id>` picks that one up again, and
  `customer-support-chat --resume` picks up the most recent one that has not ended. Nothing
  resumes on its own, so a bare run is always a clean start.
- **Streamlit:** the id is kept in the page URL (`?session=<id>`). Reloading the page, or
  reopening that URL after a server restart, resumes the conversation. Anyone holding the
  URL can read it, which is fine for a local app and needs revisiting before any real
  deployment.
- A conversation that already ended shows its transcript and says so; start a new one from
  the button (Streamlit) or by running the command again (terminal). A conversation also
  ends if the bot still cannot identify you after three tries; it says so and you start a
  new one (a conversation that ended this way is not resumable).

Design and limits: `docs/Persistence-Design.md`.

## Tests

```bash
pytest
```

Unit tests cover the deterministic graph framework (`Node`/`Edge` control
flow, retry-counter bookkeeping, `MessageHistory`, config/provider
selection) and run without Ollama or any network access. LLM-dependent
behavior (tool-calling, RAG answers, structured extraction) is exercised
manually against a live Ollama server rather than in this suite, since it's
slow and non-deterministic by nature.

## Contributing

Branching, commit and PR conventions, the pre-commit hook and CI are described
in [`docs/Git-Workflow.md`](docs/Git-Workflow.md). After cloning, enable the
hook once with `git config core.hooksPath .githooks`.

## Updating the knowledge base

The Chroma index in `chroma_db/` is only built once per tier (it's reused on
every later run to avoid re-embedding on each process start), so edits under
`assets/free` or `assets/paid` are not picked up until you rebuild it:

```bash
python scripts/reindex_kb.py            # rebuild both tiers
python scripts/reindex_kb.py --tier free
python scripts/reindex_kb.py --check    # report only; exit 1 if the index is out of date
```

Stop the app first, and keep Ollama running (it computes the embeddings). If
you forget to reindex, the app logs a warning at startup naming the stale tier
instead of silently answering from the old content.

## Configuration reference

All settings are read from environment variables / `.env` via
`src/customer_support_app/config.py`'s `Settings` (pydantic-settings). See
`.env.example` for the full list, including `AGENT_VERBOSE` (LangChain's
step-by-step tool-call tracing, off by default), `ASSETS_DIR`/`CHROMA_DIR`
overrides, and `LLM_MAX_TOKENS` / `LLM_TIMEOUT_SECONDS` (the per-call generation cap and
wait limit; a call that times out becomes a "please try again" reply).
