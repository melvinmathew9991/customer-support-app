"""Rebuild the Chroma knowledge-base indexes from assets/.

The app reuses a populated index on every start (re-embedding each time would
duplicate chunks), so edits under assets/free or assets/paid are not picked up
until the index is rebuilt. This does that deterministically, without deleting
chroma_db/ by hand. Stop any running app or eval first.

Usage:
    python scripts/reindex_kb.py                 # rebuild both tiers
    python scripts/reindex_kb.py --tier free     # rebuild one tier
    python scripts/reindex_kb.py --check         # report only; exit 1 if stale

Needs the embeddings backend (Ollama by default) to be running.
"""
import argparse
import sys

from customer_support_app.tools.rag_responder import TIERS, HelpCenterAgent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tier", choices=[*TIERS, "all"], default="all")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare the index with assets/ and exit 1 if it is out of date; changes nothing",
    )
    args = parser.parse_args(argv)
    tiers = TIERS if args.tier == "all" else (args.tier,)

    agent = HelpCenterAgent()

    if args.check:
        stale = False
        for tier in tiers:
            s = agent.index_status(tier)
            state = "up to date" if s["ok"] else "STALE"
            print(
                f"{tier}: {state} (assets={s['expected_chunks']} chunks, "
                f"index={s['indexed_chunks']}, missing={s['missing']}, stale={s['extra']})"
            )
            stale |= not s["ok"]
        return 1 if stale else 0

    for tier, count in agent.reindex(tiers).items():
        print(f"{tier}: rebuilt {count} chunks")

    still_stale = [t for t in tiers if not agent.index_status(t)["ok"]]
    if still_stale:
        names = ", ".join(still_stale)
        print(f"ERROR: index still differs from assets/ for: {names}", file=sys.stderr)
        return 1
    print("Index matches assets/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
