# Design — Customer Support App

The current `app.py` is an unstyled default Streamlit app (bare
`st.title("Hi, I'm your Shopify Agent")` + chat + a Graph tab). No theme has
been applied yet — this document defines the target visual style for when
UI polish is picked up (see `Phases.md` Phase 9), so it's a spec to build
toward, not a description of what exists today.

## 1. Brand tone
E-commerce/Shopify-adjacent support tool: calm, competent, unobtrusive. The
UI should feel like a help widget, not a marketing surface — the product is
the conversation, not the chrome around it.

## 2. Color palette
Use a small, purposeful palette — a primary brand color, a neutral scale for
surfaces/text, and status colors, each with a dark-mode pairing (Streamlit
supports light/dark via `.streamlit/config.toml` `[theme]`).

| Role | Light | Dark | Usage |
|---|---|---|---|
| Primary | `#1F6F3F` (Shopify-esque green) | `#3FBF6C` | Buttons, links, active tab, user's own chat bubble accent |
| Background | `#FFFFFF` | `#0E1117` | Page background (Streamlit default dark bg) |
| Secondary background | `#F5F6F7` | `#1A1D23` | Chat bubbles, cards, the Graph tab panel |
| Text (primary) | `#1A1A1A` | `#E6E6E6` | Body copy |
| Text (muted) | `#6B7280` | `#9AA0A6` | Timestamps, subscription-tier labels, retry hints |
| Success | `#1F6F3F` | `#3FBF6C` | "ticket created" / call-confirmed messages |
| Warning/retry | `#B45309` | `#D99B4E` | `RETRY_PROMPT` messages (invalid email/phone, etc.) |

Never use color alone to distinguish free vs. paid tier content — pair it
with a text label (see §4), since the tier distinction is a business rule,
not decoration.

## 3. Typography
- **UI font:** Streamlit's default system font stack is fine — don't fight
  the framework by injecting a custom webfont for body text; it adds load
  time for no material benefit in a support-widget context.
- **Headings** (`st.title`, tab labels): keep short and functional — e.g.
  "Support" rather than a restated brand tagline; the current
  `"Hi, I'm your Shopify Agent"` is copy for the *greeting message* inside
  the chat, not the page title, and should move there once this phase is
  picked up.
- **Chat bubbles:** normal weight body text; assistant messages left-
  aligned, user messages right-aligned (Streamlit `st.chat_message` default
  behavior) — don't override this with custom HTML/CSS unless there's a
  concrete need.
- **Monospace** only for the ticket summary block (`CallCustomerNode`'s
  output) and the Graph tab, where structure/inspectability matters more
  than prose readability.

## 4. Component/style notes
- **Chat tab:** standard `st.chat_message`/`st.chat_input`. Assistant
  "thinking"/tool-call steps stay hidden by default (matches
  `AGENT_VERBOSE=false`) — don't surface raw tool-call traces in the chat
  UI; that's a debug concern (`LOG_LEVEL`), not a user-facing one.
- **Subscription tier indicator:** once a user is identified
  (`AuthenticatedUserNode`), show their name + tier as a small badge/caption
  near the top of the chat (e.g. `st.caption`), styled with the muted text
  color — reinforces which knowledge base is answering them without being
  loud about it.
- **Graph tab:** keep the Graphviz DAG rendering as the technical/debug view
  it already is — don't restyle it to look like a marketing diagram; its
  job is inspectability of the current conversation state.
- **Retry prompts:** style with the warning color/tone above so a user
  recognizes "I didn't understand that" as a retry, not a new topic.
- **Ticket confirmation (CallCustomerNode):** use the success color for the
  confirmation message; keep the ticket summary visually distinct (e.g. a
  bordered `st.container`/code block) from ordinary chat prose.

## 5. Implementation notes
- Apply the palette via `.streamlit/config.toml`'s `[theme]` section
  (`primaryColor`, `backgroundColor`, `secondaryBackgroundColor`,
  `textColor`, `font`) rather than injecting custom CSS/HTML into `app.py`
  — stay inside Streamlit's theming API as long as it can express the
  above; only reach for `st.markdown(..., unsafe_allow_html=True)` styling
  if something here genuinely can't be expressed through it.
- Any new visual treatment (badges, ticket container, retry styling) should
  degrade gracefully in both light and dark mode — check both before
  calling a UI change done.
