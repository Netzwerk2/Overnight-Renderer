from typing import Optional


class RenderInfo:
    def __init__(
        self, frame: Optional[str], time: Optional[str], remaining: Optional[str],
        mem: Optional[str], layer: Optional[str], status: Optional[str]
    ) -> None:
        self.frame = frame
        self.time = time
        self.remaining = remaining
        self.mem = mem
        self.layer = layer
        self.status = status

    def __str__(self) -> str:
        entries = [
            self.frame, self.time, self.remaining, self.mem, self.layer,
            self.status
        ]
        return " | ".join([e for e in entries if e is not None])
