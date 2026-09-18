"""Terminal chat entrypoint. Registered as the `customer-support-chat`
console script in pyproject.toml.
"""
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.logging_config import setup_logging
from customer_support_app.pipeline import CustomerSupportPipeline


def _print_messages(res):
    if res is not None:
        for out in res:
            if isinstance(out, MessageOutput):
                print(out.message)


def main() -> None:
    setup_logging()

    pipeline = CustomerSupportPipeline()
    res, is_over = pipeline.run("")
    _print_messages(res)

    while not is_over:
        query = input()
        res, is_over = pipeline.run(query)
        _print_messages(res)


if __name__ == "__main__":
    main()
