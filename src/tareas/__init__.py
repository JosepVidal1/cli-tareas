__version__ = "1.0.0"


def main() -> None:
    from tareas.cli import app

    app()


__all__ = ["__version__", "main"]
