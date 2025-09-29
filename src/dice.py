"""
A module to model polyhedral dice.

While this isn't hugely useful for TTRPG design or literary work,
it does do some predictions of the expected distribution of
a few simple dice mechanics.

Used as a library
=================

In Rogue-like games, Gold is generally uniform distribution
between :math:`2l` and :math:`16l` for a given level, :math:`l`.
This module defines a :py:class:`UniformValue` class for this.

    >>> import random
    >>> random.seed(42)

    >>> level = 1
    >>> gold_u = UniformValue(2 * level, 16 * level)
    >>> gold_u.min, gold_u.max, 2*level, 16*level
    (2, 16, 2, 16)
    >>> gold_u.roll()
    12

A slightly more colorful approach is to use a more normal distribution.

    >>> level = 1
    >>> gold_1 = (3 * level) * D6 - level
    >>> gold_1.min, gold_1.max, 2*level, 16*level
    (2, 17, 2, 16)
    >>> str(gold_1)
    '3D6-1'
    >>> repr(gold_1)
    '3 * D6 -1'

    >>> level = 2
    >>> gold_2 = (3 * level) * D6 - level
    >>> gold_2.min, gold_2.max, 2*level, 16*level
    (4, 34, 4, 32)

    >>> level = 3
    >>> gold_3 = (3 * level) * D6 - level
    >>> gold_3.min, gold_3.max, 2*level, 16*level
    (6, 51, 6, 48)

Using the library directly
==========================

..  code-block:: bash

    PYTHONPATH=src python -c 'from dice import *; print((3*D6+2).roll())'

CLI
====

..  code-block:: bash

    python tools/src/dice.py '3*D6+2'

The shell ``'`` apostrophes are required.

Interactive

..  code-block:: bash

    python tools/src/dice.py -i
    Enter a Python-syntax dice expressions, like 3*D6+2.
    [dice] (4*D6).kh(3)
    6
    [dice] count 6
    [6 rolls] (4*D6).kh(3)
    7
    14
    13
    14
    11
    12
    [6 rolls]
    10
    14
    12
    15
    16
    10
    [6 rolls]

"""

from cmd import Cmd
import math
from random import randint, seed
import sys
from textwrap import dedent
from typing import Any, Annotated, Self

import typer
import rich


class Die:
    """
    Creates a useful source of random numbers from a "die expression".
    A die expression can also provide some expected value information for most (not all) cases.
    The syntax uses Python objects and operators.

    Examples:

    >>> from random import seed
    >>> seed(42)

    The base objects, D4, D6, etc.
    >>> D6.roll()
    6

    A dice expression in Python syntax.
    >>> d = 3 * D6
    >>> d.roll()
    8
    >>> d.pool()
    [2, 2, 3]
    >>> str(d)
    '3D6'

    A set of dice rolls. Note ``d = 3 * D6``.
    >>> roll10 = [(d - 3).roll() for i in range(10)]
    >>> roll10
    [6, 14, 7, 0, 6, 8, 11, 12, 8, 3]

    Expected values.
    >>> d.min
    3
    >>> d.max
    18
    >>> d.mean
    10.5
    >>> d.stdev  # doctest: +ELLIPSIS
    2.958...

    The "roll 4d6 keep the highest 3" expression.
    The ()'s are required.
    >>> char = (4 * D6).kh(3)
    >>> char.pool()
    [3, 4, 6]

    Expected Values
    ---------------

    The expected values are exact, and can do things like transform
    a dice value into a z-score: ``(d.roll() - d.mean) / d.stdev``.
    This will have value from about -3 to about +3 and can be used to
    turn a number into a descriptive summary.

    The predictions do **not** account for ``kh()`` modifiers.

    See https://rpubs.com/Avijit0616/698613

    The expected values are the basis for comparison among two Die instances.
    >>> D8 > D6
    True

    Note
    ----

    A thing that "seems" to behave inconsistently
    in unit tests.

    >>> seed(42)
    >>> [r for r in range(10) if D20.roll() >= 13]
    [7, 9]
    """

    def __init__(
        self,
        d: int,
        *,
        n: int | None = None,
        adj: int | None = None,
        keep: int | None = None,
    ) -> None:
        """
        Create a Die instance. This is rarely used, since the common polyhedral die are already provided.

        :param d: the number of faces.
        :param n: the number of dice in the dice pool.
        :param adj: the adjustment to add to the total.
        :param keep: the number of the highest values to keep.
        """
        self.faces = d
        self.n = n or 1
        self.adj = adj or 0
        self.keep = keep or self.n

    def __str__(self) -> str:
        text = f"{self.n}D{self.faces}"
        if self.adj:
            text = f"{text}{self.adj:+d}"
        if self.keep != self.n:
            text = f"{text} (k{self.keep})"
        return text

    def __repr__(self) -> str:
        text = f"{self.n} * D{self.faces}"
        if self.adj:
            text = f"{text} {self.adj:+d}"
        if self.keep != self.n:
            text = f"({text}).kh({self.keep})"
        return text

    def __eq__(self, other: Any) -> bool:
        match other:
            case Die():
                return (
                    self.faces == other.faces
                    and self.n == other.n
                    and self.adj == other.adj
                    and self.keep == other.keep
                )
            case _:  # pragma: no cover
                return NotImplemented

    def __gt__(self, other: Any) -> bool:
        match other:
            case Die():
                return self._domain > other._domain
        return NotImplemented  # pragma: no cover

    def __lt__(self, other: Any) -> bool:
        match other:
            case Die():
                return self._domain < other._domain
        return NotImplemented  # pragma: no cover

    def __ge__(self, other: Any) -> bool:
        match other:
            case Die():
                return self._domain >= other._domain
        return NotImplemented  # pragma: no cover

    def __le__(self, other: Any) -> bool:
        match other:
            case Die():
                return self._domain <= other._domain
        return NotImplemented  # pragma: no cover

    @property
    def min(self) -> int:
        return self.n + self.adj

    @property
    def max(self) -> int:
        return self.n * self.faces + self.adj

    @property
    def _domain(self) -> int:
        return self.n * self.faces + self.adj

    @property
    def mean(self) -> float:
        """
        For "keep high" rules, we *could* enumerate all possible rolls.
        Its this::

            rolls = chain(*self.n * [range(1, 1 + self.faces)])
            rolls_kh = (sorted(r)[-self.keep:] for r in rolls)
            domain = [sum(r) + self.adj for r in rolls_kh]

            d_m = mean(domain)
            d_s = stdev(domain)
        """
        assert self.keep == self.n, "Can't predict mean with kh()"
        return (self.max - self.min) / 2 + self.min

    @property
    def stdev(self) -> float:
        assert self.keep == self.n, "Can't predict stdev with kh()"
        # var_1d = (
        #     sum(p**2 for p in range(1, self.faces + 1)) / self.faces
        #     - ((1 + self.faces) / 2) ** 2
        # )
        var_1d = (
            self.faces**3 / 3 + self.faces**2 / 2 + self.faces / 6
        ) / self.faces - ((1 + self.faces) / 2) ** 2
        return math.sqrt(var_1d * self.n)

    def pool(self) -> list[int]:
        """A collection of dice with the "keep-high" applied."""
        base = list(randint(1, self.faces) for _ in range(self.n))
        return sorted(base)[-self.keep :]

        # Or this...
        # def kh(dice: list[int], n: int) -> list[int]:
        #     if n == 0: return []
        #     m = max(dice)
        #     dice.remove(m)
        #     return [m] + kh(dice, n-1)
        # return kh(base, self.keep)

        # Or this...
        # for k in range(self.n - self.keep):
        #     base.remove(min(base))
        # return base

    def roll(self) -> int:
        """The sum of the dice pool with the adjustment applied."""
        return sum(self.pool()) + self.adj

    def __rmul__(self, other: Any) -> Self:
        """Implement int * Die."""
        match other:
            case int():
                return self.__class__(self.faces, n=self.n * other, adj=self.adj)
        return NotImplemented  # pragma: no cover

    def __add__(self, other: Any) -> Self:
        """Implement Die + int."""
        match other:
            case int():
                return self.__class__(self.faces, n=self.n, adj=self.adj + other)
        return NotImplemented  # pragma: no cover

    def __sub__(self, other: Any) -> Self:
        """Implement Die - int."""
        match other:
            case int():
                return self.__class__(self.faces, n=self.n, adj=self.adj - other)
        return NotImplemented  # pragma: no cover

    def kh(self, keep: int | None = None) -> Self:
        """Creates new Die with the keep highest "keep" values."""
        return self.__class__(self.faces, n=self.n, adj=self.adj, keep=keep or self.n - 1)


D4 = Die(4)

D6 = Die(6)

D8 = Die(8)

D10 = Die(10)

D12 = Die(12)

D20 = Die(20)

D100 = Die(100)
PCT = D100


class FixedValue(Die):
    """
    A single, fixed value. Weird, right?

    This is compatible with :py:class:`Die` to permit aggregation of distinct domains.
    It's slightly more efficient than ``UniformValue(x, x)``,
    """

    def __init__(self, value: int) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def __eq__(self, other: Any) -> bool:
        match other:
            case FixedValue():
                return self.value == other.value
            case _:  # pragma: no cover
                return NotImplemented  # pragma: no cover

    def __gt__(self, other: Any) -> bool:
        match other:
            case FixedValue():
                return self.value > other.value
        return NotImplemented  # pragma: no cover

    def __lt__(self, other: Any) -> bool:
        match other:
            case FixedValue():
                return self.value < other.value
        return NotImplemented  # pragma: no cover

    def __ge__(self, other: Any) -> bool:
        match other:
            case FixedValue():
                return self.value >= other.value
        return NotImplemented  # pragma: no cover

    def __le__(self, other: Any) -> bool:
        match other:
            case FixedValue():
                return self.value <= other.value
        return NotImplemented  # pragma: no cover

    @property
    def min(self) -> int:
        return self.value

    @property
    def max(self) -> int:
        return self.value

    @property
    def mean(self) -> float:
        return self.value

    @property
    def stdev(self) -> float:
        return 1.0  # Not really

    def roll(self) -> int:
        return self.value

class WildDie(Die):
    """
    The "Wild Die" mechanic for OpenD6 games.

    >>> seed(42)
    >>> dice = 5 * WildDie(6)
    >>> dice.roll()
    17
    >>> dice.wild
    'success'
    >>> dice.roll()
    23
    >>> dice.wild
    'success'
    >>> dice.roll()
    18
    >>> dice.wild
    ''
    """
    wild: str

    def kh(self, keep: int | None = None) -> Self:
        raise TypeError("not supported: kh()")

    def pool(self) -> list[int]:
        """A collection of dice."""
        return list(randint(1, self.faces) for _ in range(self.n))

    def roll(self) -> int:
        dice = self.pool()
        if dice[0] == 1:
            self.wild = "failure"
            return sum(dice)
        elif dice[0] == self.faces:
            self.wild = "success"
            total = 0
            while dice[0] == self.faces:
                total += sum(dice)
                dice = self.pool()
            return total
        else:
            self.wild = ""
            return sum(dice)


class UniformValue(Die):
    """
    A uniformly distributed value on the **closed** interval. Both ends included.
    Used with Aggregates that have a uniform distribution of instances.

    This is compatible with :py:class:`Die` to permit aggregation of distinct domains.
    """

    def __init__(self, low: int, high: int) -> None:
        self.low = low
        self.high = high

    def __str__(self) -> str:
        return f"{self.low}..{self.high}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.low}, {self.high})"

    def __eq__(self, other: Any) -> bool:
        match other:
            case UniformValue():
                return self.low == other.low and self.high == other.high
            case _:  # pragma: no cover
                return NotImplemented

    def __gt__(self, other: Any) -> bool:
        match other:
            case UniformValue():
                return self.low > other.low or self.high > other.high
        return NotImplemented  # pragma: no cover

    def __lt__(self, other: Any) -> bool:
        match other:
            case UniformValue():
                return self.low < other.low or self.high < other.high
        return NotImplemented  # pragma: no cover

    def __ge__(self, other: Any) -> bool:
        match other:
            case UniformValue():
                return self.low >= other.low or self.high >= other.high
        return NotImplemented  # pragma: no cover

    def __le__(self, other: Any) -> bool:
        match other:
            case UniformValue():
                return self.low <= other.low or self.high <= other.high
        return NotImplemented  # pragma: no cover

    @property
    def min(self) -> int:
        return self.low

    @property
    def max(self) -> int:
        return self.high

    @property
    def mean(self) -> float:
        return (self.low + self.high) / 2

    @property
    def stdev(self) -> float:
        # return statistics.stdev(range(self.low, self.high+1))
        return math.sqrt(
            2
            * (((self.low + self.high) / 2) ** 2 + self.low + self.high)
            / (self.high - self.low)
        )

    def roll(self) -> int:
        return randint(self.low, self.high)


class Interaction(Cmd):
    """An Interactive dice roller."""

    prompt = "[dice] "
    namespace: dict[str, Die]

    def preloop(self) -> None:
        self.count = 1
        self.dice_expr: Die | None = None

    def do_help(self, arg: str) -> bool | None:
        """Provide some guidance."""
        if arg:
            return super().do_help(arg)
        else:
            defined_dice = ", ".join(self.namespace.keys())
            help = dedent(f"""\
            Enter a dice expression in Python syntax, for example [bold]3*D6+2[/bold].
            The '*' is required. It's Python, after all.
            For a 'keep highest' roll, use ()'s and a [bold].kh()[/bold] suffix.
            For example, [bold](4*D6).kh(3)[/bold]
            All the syntax is required.
            The pre-defined polyhedral die types are: {defined_dice}
            """)
            rich.print(help)
            if self.dice_expr:
                rich.print(
                    f"Currently rolling {self.count} instance{'' if self.count == 1 else 's'} of {self.dice_expr!r}"
                )
            return super().do_help("")

    def do_quit(self, arg: str) -> bool | None:
        """Exit the the dice-roller."""
        return True

    do_exit = do_quit
    do_EOF = do_quit

    def do_count(self, arg: str) -> bool | None:
        """Set the number of times to roll the dice expression."""
        if not arg:
            rich.print(f"Rolling {self.count} times")
            return False
        try:
            self.count = int(arg)
            if self.dice_expr:
                self.emptyline()
            else:
                rich.print(f"Rolling {self.count} times")
        except ValueError:
            rich.print(f"Invalid {arg!r} value for count")
        return False

    def do_expect(self, arg: str) -> bool | None:
        """Display expected ranges of values of a dice expression."""
        if arg:
            self._parse(arg)
        if not self.dice_expr:
            rich.print("No dice expression provided")
            return False
        rich.print(repr(self.dice_expr))
        rich.print(f"range: {self.dice_expr.min} - {self.dice_expr.max}")
        rich.print(f"mean: {self.dice_expr.mean:.2f}")
        rich.print(f"standard deviation: {self.dice_expr.stdev:.3f}")
        return False

    def emptyline(self) -> bool:
        """Roll the most recently-parsed dice expression."""
        if not self.dice_expr:
            rich.print("Enter a valid dice expression. For help, type help.")
            return False
        for _ in range(self.count):
            output = self.dice_expr.roll()
            rich.print(output)
        return False

    def default(self, line: str) -> None:
        """Parse this line, assuming it's a dice expression."""
        self._parse(line)
        self.emptyline()

    def _parse(self, line: str) -> None:
        try:
            code_obj = compile(line, "<interactive>", mode="eval")
            self.dice_expr = eval(
                code_obj, globals=self.namespace, locals=self.namespace
            )
        except BaseException as err:
            rich.print(f"the dice expression [bold]{line!r}[/bold] does not compute")

    def postcmd(self, stop: bool, line: str) -> bool:
        if self.dice_expr:
            self.prompt = f"[{self.count} roll{'' if self.count == 1 else 's'} of {self.dice_expr!r}] "
        else:
            self.prompt = "[dice] "
        return stop


dice_app = typer.Typer()


@dice_app.command()
def main(
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Start an interactive session")
    ] = False,
    expected_value: Annotated[
        bool,
        typer.Option(
            "--expected",
            "-e",
            help="Show the expected range, mean, and standard deviation",
        ),
    ] = False,
    count: Annotated[
        int, typer.Option("--count", "-c", help="number of times to roll")
    ] = 1,
    expression: Annotated[
        str,
        typer.Argument(
            help="Dice expression, example: '2*D6+3' (quotes are *required*)"
        ),
    ] = "",
    seed_value: Annotated[
        str | None,
        typer.Option("--seed", help="Impose a seed for reproducible random numbers"),
    ] = None,
):
    """
    Either provide a Python-syntax dice expression or start an interactive command loop.
    The Python syntax means the `*` is required for '3*D6'.
    """
    namespace = {
        "D4": D4,
        "D6": D6,
        "D8": D8,
        "D10": D10,
        "D12": D12,
        "D20": D20,
        "D100": D100,
        "PCT": D100,
    }

    if seed_value:
        seed(seed_value.encode("ascii"))

    if interactive:
        if expression:
            sys.exit(f"Extra command-line argument value found: {expression}")
        cmd = Interaction()
        cmd.namespace = namespace
        cmd.cmdloop("Enter a Python-syntax dice expressions, like 3*D6+2.")

    else:
        try:
            code_obj = compile(expression, "<argument>", mode="eval")
            d = eval(code_obj, globals=namespace, locals=namespace)
        except BaseException as err:
            sys.exit(f"The dice expression {expression!r} does not compute")
        if expected_value:
            print(repr(d))
            print(f"range: {d.min} - {d.max}")
            print(f"mean: {d.mean:.2f}")
            print(f"standard deviation: {d.stdev:.3f}")
        else:
            for _ in range(count):
                output = d.roll()
                print(output)


if __name__ == "__main__":
    dice_app()
