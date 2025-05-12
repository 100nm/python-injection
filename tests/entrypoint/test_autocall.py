from injection.entrypoint import autocall


def test_autocall_with_success():
    count = 0

    @autocall
    def increment() -> None:
        nonlocal count
        count += 1

    assert count == 1
