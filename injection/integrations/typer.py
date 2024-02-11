from typing import Annotated, TypeVar

from typer import Exit, Option, colors, echo, style

from injection import Module, default_module

_T = TypeVar("_T")


def injected(cls: type[_T], module: Module = default_module) -> type[_T]:
    def parser(value: _T | str):
        if isinstance(value, str):
            message = style(
                "Injected options don't support custom input.",
                fg=colors.RED,
                bold=True,
            )
            echo(message)
            raise Exit(code=1)

        return value

    return Annotated[
        cls,
        Option(
            default_factory=lambda: module.get_instance(cls),
            parser=parser,
            hidden=True,
        ),
    ]
