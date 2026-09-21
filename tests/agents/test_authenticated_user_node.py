from customer_support_app.agents.support import AuthenticatedUserNode
from customer_support_app.domain.chat import Role
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.domain.validation import UserProfile

MICHAEL = UserProfile(
    name="Michael Jackson",
    email="michaeljackson@gmail.com",
    subscription="premium",
    user_id=1,
    phone="0452 333 666",
    language="English",
)


def _node_with_input(node_input) -> AuthenticatedUserNode:
    # Bypass __init__: it builds a help-center agent, which needs a Chroma index and a model.
    node = AuthenticatedUserNode.__new__(AuthenticatedUserNode)
    node.set_node_input(node_input)
    return node


def test_an_identified_user_keeps_the_conversation_going():
    assert _node_with_input(MICHAEL).is_node_final() is False


def test_a_failed_identification_ends_the_conversation():
    # What UserInfoChainBasedEdge hands over once it runs out of retries (#37).
    error = MessageOutput("no matching record", role=Role.SYSTEM)

    node = _node_with_input(error)

    assert node.is_node_final() is True
    assert "couldn't verify your account" in node.greeting_message().message
