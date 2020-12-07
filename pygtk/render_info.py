from typing import Optional

from config import Config


class RenderInfo:
    def __init__(
        self, frame: Optional[str], time: Optional[str], remaining: Optional[str],
        mem: Optional[str], layer: Optional[str], status: Optional[str], config: Config
    ) -> None:
        self.frame = frame
        self.time = time
        self.remaining = remaining
        self.mem = mem
        self.layer = layer
        self.status = status
        self.config = config

    def __str__(self) -> str:
        entries = []
        for entry in self.config.settings["render_info"]:
            if entry["visible"]:
                entries.append(getattr(self, entry["name"]))

        return " | ".join([e for e in entries if e is not None])
