from typer import Option

__all__ = ("ignore",)


def ignore():
    """
    Typer option for the CLI to ignore this option and replace it with `None`.
    """

    return Option(
        default_factory=str,
        parser=lambda _: None,
        hidden=True,
    )
