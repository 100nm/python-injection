__all__ = ("sentinel",)


class Sentinel:
    __slots__ = ()

    def __bool__(self) -> bool:
        return False  # pragma: no cover


sentinel = Sentinel()

del Sentinel
