__version__ = "0.1.0"


def main() -> None:
    from tareas.cli import app

    app()


__all__ = ["__version__", "main"]
