from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Dict, Any


@dataclass
class Message:
    topic: str
    key: str
    value: Dict[str, Any]


class KafkaConsumerStub:
    def __init__(self, topic: str) -> None:
        self.topic = topic

    def poll(self, handler: Callable[[Message], None], limit: int = 5) -> int:
        count = 0
        for idx in range(limit):
            msg = Message(topic=self.topic, key=f"{self.topic}-{idx}", value={"payload": idx})
            handler(msg)
            count += 1
        return count


__all__ = ["KafkaConsumerStub", "Message"]
