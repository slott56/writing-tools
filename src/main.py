"""
Main UI/interaction code and definitions for the Command-Line Interface (CLI).

Does its best to use Typer and Rich to separate out core logic from console display, etc.
"""

from sys import stderr
from typing import Annotated

from rich import print
import typer

from names import generate_names
from features import generate_features


app = typer.Typer(no_args_is_help=True)


def eprint(*args, **kwargs) -> None:
    """
    Print only to stderr.
    """
    print(*args, file=stderr, **kwargs)


def highlight_list_items(items: list[str], *, color: str = "green") -> str:
    """
    Highlights list items using Rich terminal color markup.
    """
    highlighted = map(lambda s: f"[{color}]{s}[/]", items)

    return ", ".join(highlighted)


@app.command(
    short_help="Produce n random English words",
    help="Select n random words from the English-language corpus and print them, one per line.",
)
def words(n: Annotated[int, typer.Argument()] = 6) -> None:
    eprint(f"Selecting [green]{n}[/green] random words...\n", file=stderr)

    names = generate_names(n)

    for name in names:
        typer.echo(name)


@app.command(
    short_help="Features and descriptions of characters",
    help="Generate randomized features to describe named characters. You supply the names.",
)
def features(
    names: list[str],
    defaults: Annotated[bool, typer.Option(help="Use Default Characters")] = False,
) -> None:
    if defaults or len(names) < 1:
        char_names = [
            "Farrier",
            "Little Smith",
            "Fletcher",
            "Cobbler",
            "Swineherd",
            "Goatherd",
            "Mouth",
            "Big Smith",
            "Tinker",
        ]
    else:
        char_names = names

    eprint(
        f"Generating [green]{len(char_names)}[/] characters for {highlight_list_items(char_names)}.\n"
    )

    character_tables = generate_features(character_names=char_names)

    for table in character_tables:
        print(table)
        print()


if __name__ == "__main__":
    app()
