from __future__ import annotations

from dataclasses import dataclass

from scripts import manage_prompts


@dataclass
class FakePrompt:
    version: int


class FakePromptClient:
    def __init__(self) -> None:
        self.next_version = 1
        self.labels: dict[str, int] = {}
        self.created: list[dict] = []

    def get_prompt(self, name: str, *, label: str, **kwargs):
        if label not in self.labels:
            raise type("NotFoundError", (Exception,), {})()
        return FakePrompt(self.labels[label])

    def create_prompt(self, **kwargs):
        version = self.next_version
        self.next_version += 1
        self.created.append(kwargs)
        for label in kwargs["labels"]:
            self.labels[label] = version
        return FakePrompt(version)

    def update_prompt(self, *, version: int, new_labels: list[str], **kwargs):
        for label, current_version in list(self.labels.items()):
            if current_version == version and label not in new_labels:
                del self.labels[label]
        for label in new_labels:
            self.labels[label] = version


def test_prompt_lifecycle_is_idempotent(monkeypatch) -> None:
    client = FakePromptClient()
    monkeypatch.setattr(manage_prompts, "write_audit", lambda *args, **kwargs: {})

    initial = manage_prompts.bootstrap_prompts(client)
    repeated = manage_prompts.bootstrap_prompts(client)
    promoted = manage_prompts.promote_candidate(client)
    rolled_back = manage_prompts.rollback_production(client)

    assert initial == {"baseline": 1, "candidate": 2, "production": 1}
    assert repeated == initial
    assert len(client.created) == 2
    assert promoted["production"] == 2
    assert rolled_back["production"] == 1
