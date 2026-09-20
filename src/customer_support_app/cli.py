"""Terminal chat entrypoint. Registered as the `customer-support-chat` console script in
pyproject.toml.

A conversation is saved after every turn. Run it bare to start a new one (its id is printed),
`--session ID` to pick that one up again, or `--resume` for the most recent unfinished one.
"""
import argparse
import sys
from typing import List, Optional

from customer_support_app.config import get_settings
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.logging_config import setup_logging
from customer_support_app.pipeline import CustomerSupportPipeline
from customer_support_app.session_store import SessionStore, SessionStoreError

QUIT_COMMANDS = {"quit", "exit"}
GOODBYE = "Goodbye."


def _print_messages(res):
    if res is not None:
        for out in res:
            if isinstance(out, MessageOutput):
                print(out.message)


def _print_transcript(pipeline) -> None:
    for message in pipeline.transcript():
        print(f"You: {message['content']}" if message["role"] == "user" else message["content"])


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="customer-support-chat", description="Chat with the customer support agent."
    )
    which = parser.add_mutually_exclusive_group()
    which.add_argument(
        "--session",
        metavar="ID",
        help="pick up the saved conversation with this id (or start one under it)",
    )
    which.add_argument(
        "--resume",
        action="store_true",
        help="pick up the most recent conversation that has not ended",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    setup_logging()

    try:
        store = SessionStore(get_settings().session_db_path)
    except SessionStoreError as error:
        print(f"Cannot use the saved-conversation database: {error}", file=sys.stderr)
        sys.exit(1)

    session_id = args.session
    if args.resume:
        session_id = store.latest_unfinished()
        if session_id is None:
            print("No unfinished conversation to resume; starting a new one.")

    pipeline = CustomerSupportPipeline(store=store, session_id=session_id)

    if pipeline.resumed:
        print(f"Resuming conversation {pipeline.session_id}.\n")
        _print_transcript(pipeline)
        if pipeline.ended:
            print("\nThis conversation has ended. Run customer-support-chat to start a new one.")
            return
        is_over = False
    else:
        if session_id is not None:
            print(
                f"Could not resume '{session_id}' (not found, or not resumable); "
                "starting a new conversation under that id."
            )
        print(
            f"Session {pipeline.session_id} - pick it up later with: "
            f"customer-support-chat --session {pipeline.session_id}"
        )
        res, is_over = pipeline.run("")
        _print_messages(res)

    while not is_over:
        try:
            query = input()
        except EOFError:
            # Piped input ended, or Ctrl+D / Ctrl+Z: leave cleanly instead of a traceback.
            print(GOODBYE)
            return
        if query.strip().lower() in QUIT_COMMANDS:
            print(GOODBYE)
            return
        res, is_over = pipeline.run(query)
        _print_messages(res)


if __name__ == "__main__":
    main()
