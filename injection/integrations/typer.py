from typing import Annotated, TypeVar

from typer import Exit, Option, colors, echo, style

from injection import Module, default_module

_T = TypeVar("_T")


def injected(cls: type[_T], module: Module = default_module) -> type[_T]:
    def parser(value: str | None):
        if value:
            message = style(
                "Injected options don't support custom input.",
                fg=colors.RED,
                bold=True,
            )
            echo(message)
            raise Exit(code=1)

        return module.get_instance(cls, none=False)

    return Annotated[
        cls,
        Option(
            default_factory=lambda: "",
            parser=parser,
            hidden=True,
        ),
    ]
