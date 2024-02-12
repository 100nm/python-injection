from typing import Annotated

import pytest
from typer import Typer
from typer.testing import CliRunner

from injection import inject, singleton
from injection.integrations.typer import ignore


@singleton
class Dependency:
    pass


app = Typer()


@app.command()
@inject(force=True)
def integration(dependency: Annotated[Dependency, ignore()]):
    assert isinstance(dependency, Dependency)


class TestInjected:
    @pytest.fixture(scope="class")
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_injected_with_success(self, runner):
        result = runner.invoke(app)
        assert result.exit_code == 0

    def test_injected_with_custom_input(self, runner):
        result = runner.invoke(app, ["--dependency", "input"])
        assert result.exit_code == 0
