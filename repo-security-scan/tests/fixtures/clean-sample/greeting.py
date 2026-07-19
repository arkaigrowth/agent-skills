"""A deliberately trivial, safe module. No imports, no I/O, no subprocess."""


def greet(name: str) -> str:
    """Return a friendly greeting for the given name."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("world"))
