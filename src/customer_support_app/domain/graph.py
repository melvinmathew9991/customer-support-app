import dataclasses
from typing import TYPE_CHECKING, List, Optional, Union

from pydantic import BaseModel

from customer_support_app.domain.chat import Role

if TYPE_CHECKING:
    # Type-checking only: graph.node imports this module, so a runtime import would be circular.
    from customer_support_app.graph.node import BaseNode


@dataclasses.dataclass
class MessageOutput:
    message: str
    role: Role


@dataclasses.dataclass
class EdgeOutput:
    should_continue: bool
    result: Union[BaseModel, str]
    message_output: Optional[List[MessageOutput]]
    num_fails: int
    next_node: Optional["BaseNode"]
