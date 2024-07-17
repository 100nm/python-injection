import inspect
import itertools
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from statistics import mean
from timeit import timeit
from typing import Annotated, Any, ClassVar, Self

from tabulate import tabulate
from typer import Option, Typer

from injection import inject, injectable


@dataclass(frozen=True, slots=True)
class Benchmark:
    x: Decimal
    y: Decimal

    @property
    def difference_rate(self) -> Decimal:
        return ((self.y - self.x) / self.x) * 100

    @classmethod
    def compare(
        cls,
        x: Callable[..., Any],
        y: Callable[..., Any],
        number: int = 1,
    ) -> Self:
        x = mean(cls._time_in_ns(x, number))
        y = mean(cls._time_in_ns(y, number))
        return cls(x, y)

    @staticmethod
    def _time_in_ns(callable_: Callable[..., Any], number: int) -> Iterator[Decimal]:
        for _ in range(number):
            delta = timeit(callable_, number=1)
            yield Decimal(delta) * (10**6)


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    title: str
    benchmark: Benchmark

    @property
    def row(self) -> tuple[str, str, str, str]:
        rate = self.benchmark.difference_rate
        return (
            self.title,
            f"{self.benchmark.x:.2f}μs",
            f"{self.benchmark.y:.2f}μs",
            f"{rate:.2f}% slower" if rate >= 0 else f"{abs(rate):.2f}% faster",
        )


@dataclass(frozen=True, slots=True)
class InjectBenchmark:
    callables: ClassVar[dict[str, Callable[..., Any]]] = {}

    def start(self, number: int = 1) -> Iterator[BenchmarkResult]:
        for title, callable_ in self.callables.items():
            signature = inspect.signature(callable_, eval_str=True)
            dependencies = {
                name: parameter.annotation
                for name, parameter in signature.parameters.items()
            }

            def reference():
                return callable_(**{name: d() for name, d in dependencies.items()})

            first = Benchmark.compare(reference, lambda: inject(callable_)(), number)
            yield BenchmarkResult(f"{title} (first run)", first)

            injected = inject(callable_)
            injected()
            instance = Benchmark.compare(reference, injected, number)
            yield BenchmarkResult(title, instance)

    @classmethod
    def register(cls, wrapped: Callable[..., Any] = None, /, *, title: str):
        def decorator(wp):
            cls.callables[title] = wp
            return wp

        return decorator(wrapped) if wrapped else decorator


@injectable
class A:
    pass


@injectable
class B:
    pass


@injectable
class C:
    pass


@injectable
class D:
    pass


@injectable
class E:
    pass


@InjectBenchmark.register(title="0 dependency")
def function_with_0_dependency():
    pass


@InjectBenchmark.register(title="1 dependencies")
def function_with_1_dependency(__a: A):
    pass


@InjectBenchmark.register(title="2 dependencies")
def function_with_2_dependencies(__a: A, __b: B):
    pass


@InjectBenchmark.register(title="3 dependencies")
def function_with_3_dependencies(__a: A, __b: B, __c: C):
    pass


@InjectBenchmark.register(title="4 dependencies")
def function_with_4_dependencies(__a: A, __b: B, __c: C, __d: D):
    pass


@InjectBenchmark.register(title="5 dependencies")
def function_with_5_dependencies(__a: A, __b: B, __c: C, __d: D, __e: E):
    pass


cli = Typer()


@cli.command()
def main(number: Annotated[int, Option("--number", "-n", min=0)] = 1000):
    results = InjectBenchmark().start(number)
    headers = ("", "Reference Time (μs)", "@inject Time (μs)", "Difference Rate (%)")
    data = (result.row for result in itertools.chain(results))
    table = tabulate(data, headers=headers)
    print(table)


if __name__ == "__main__":
    cli()
