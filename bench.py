import itertools
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from statistics import mean
from timeit import timeit
from typing import Annotated, Any, Self

from tabulate import tabulate
from typer import Option, Typer

from injection import inject, injectable


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


def with_0_dependency():
    pass


def with_1_dependency(__a: A):
    pass


def with_2_dependencies(__a: A, __b: B):
    pass


def with_3_dependencies(__a: A, __b: B, __c: C):
    pass


def with_4_dependencies(__a: A, __b: B, __c: C, __d: D):
    pass


def with_5_dependencies(__a: A, __b: B, __c: C, __d: D, __e: E):
    pass


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
        x = mean(cls.__time_in_ns(x, number))
        y = mean(cls.__time_in_ns(y, number))
        return cls(x, y)

    @staticmethod
    def __time_in_ns(
        __callable: Callable[..., Any],
        /,
        number: int,
    ) -> Iterator[Decimal]:
        for _ in range(number):
            delta = timeit(__callable, number=1)
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


def inject_benchmark(
    title: str,
    function: Callable[..., Any],
    dependencies: Iterable[Callable[..., Any]] = (),
    number: int = 1,
) -> Iterator[BenchmarkResult]:
    def reference():
        return function(*(d() for d in dependencies))

    first = Benchmark.compare(
        reference,
        lambda: inject(function)(),
        number=number,
    )
    yield BenchmarkResult(f"{title} (first run)", first)

    injected = inject(function)
    injected()
    instance = Benchmark.compare(
        reference,
        injected,
        number=number,
    )
    yield BenchmarkResult(title, instance)


cli = Typer()


@cli.command()
def main(number: Annotated[int, Option("--number", "-n", min=0)] = 1000):
    results = map(
        lambda args: inject_benchmark(*args, number=number),
        (
            (
                "0 dependency",
                with_0_dependency,
                (),
            ),
            (
                "1 dependency",
                with_1_dependency,
                (A,),
            ),
            (
                "2 dependencies",
                with_2_dependencies,
                (A, B),
            ),
            (
                "3 dependencies",
                with_3_dependencies,
                (A, B, C),
            ),
            (
                "4 dependencies",
                with_4_dependencies,
                (A, B, C, D),
            ),
            (
                "5 dependencies",
                with_5_dependencies,
                (A, B, C, D, E),
            ),
        ),
    )

    headers = ("", "Reference Time (μs)", "@inject Time (μs)", "Difference Rate (%)")
    data = tuple(result.row for result in itertools.chain.from_iterable(results))
    table = tabulate(data, headers=headers)

    print(table)


if __name__ == "__main__":
    cli()
