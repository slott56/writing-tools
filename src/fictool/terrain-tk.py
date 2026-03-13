r"""
Terrain Generator -- Turtle/Tk

1. HexGrid

2. Terrain

3. Graphics

4. Applications

5. Test & Demo

Turtle is amazingly slow. Fun. But slow.

Hex Grid
========

Hexagonal Grid processing.

The higher-level processing includes adjancency and edge detection.

The ``HexGrid``` class embodies a bunch of rules for working with hexagons.

Terrain
=======

Paint random cells of the hexgrid.

The idea is to evolve toward an Empire of Cities.
This means build out the country surrounding each capital city incrementally
to allow interesting borders to evolve.

Empire generation in steps, useful for animation.

Cities and the Empire classes embody capital cities and surrounding domains,
and the overall Empire.

(Think of these as large hexes.
The idea is that 18 x 18 is most of Europe or the most of the US.
Each hex is about 100 miles across. r=50 miles.
Boston to Denver is about 1800 miles.
)


Graphics
========

The ``Drawing`` class hierarchy.

This includes drawing low-level hexagons with `matplotlib`.

See:

-  https://www.redblobgames.com/grids/hexagons/

-  https://www.redblobgames.com/grids/hexagons/#coordinates-doubled

Given hex radius $r$, the size of each hex is given by:

-  $h = \sqrt{3} \times r$

-  $w = 2 \times r$


Application
===========

Animation is fun -- see the empire build.

::

    python terrain-tk.py --seed=x

"""

import abc
from collections.abc import Iterator, Iterable
from functools import cache, reduce
from math import sqrt, cos, sin, radians
import os
from pathlib import Path
import random
import string
import turtle

from invoke import task, Program, Collection
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.artist import Artist
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D

# Importing this with pyplot creates problems.
# And tutle is SLOW.
# import turtle


### 1. HexGrid


class HexGrid:
    """
    Defines a tesselation of hexagons.

    By definition for 1 cell:

    ..  math::

        h = \\sqrt{3} \\times r

        w = 2 \\times r

    Coordinates are "doubled grid":
    - even columns have even row cells,
    - odd columns have odd row cells.

    Given a figure area height of $f_h$ and number of cells, $c$.
    We can compute the number of rows in the figure, $f_r$.
    From this we can compute the radius, $r$ for each hex.

    ..  math::

        f_r = \\frac{f_h}{c}

        r = \\frac{f_r}{\\sqrt {3}}

        r = \\frac{f_r}{\tfrac{1}{2}\\cos(30)}

    Note that x axis coordinates must be offset by r/2 so the 0, 0 origin is visible.

    Note that tg.degrees() is the going-in assumption, also.
    """

    def __init__(self, columns: int) -> None:
        self.columns = columns  # x-axis. Interleaved even and odd.
        self.rows = 2 * columns  # y-axis stacked but alternating.

    def all(self) -> Iterator[tuple[int, int]]:
        """
        Enumerate all the cell coordinates.

        Grid with 3 rows will have 6 columns

        >>> hg = HexGrid(3)
        >>> [hg.cell_name(*c) for c in hg.all()]
        ['1A', '1C', '1E', '2B', '2D', '2F', '3A', '3C', '3E']
        """
        for col in range(self.columns):
            for row in range(col % 2, self.rows, 2):
                yield col, row

    def random(self) -> tuple[int, int]:
        """
        Random cell; if x is odd, y is constrained to odd values.
        """
        x = random.randint(0, self.columns - 1)
        y = random.choice(range(x % 2, self.rows, 2))
        return (x, y)

    @staticmethod
    def cell_name(col: int, row: int) -> str:
        """
        Cell name using numbers across and letters down.

        Note that this is places 1A at the bottom left, when it's often at the top left.

        >>> hg = HexGrid(4)
        >>> hg.cell_name(0, 0)
        '1A'
        >>> hg.cell_name(1, 1)
        '2B'
        >>> hg.cell_name(4, 0)
        '5A'
        >>> hg.cell_name(4, 4)
        '5E'
        """
        letter1, letter2 = divmod(row, 26)
        if letter1 == 0:
            row_label = string.ascii_uppercase[letter2]
        else:
            row_label = (
                string.ascii_uppercase[letter1 - 1] + string.ascii_uppercase[letter2]
            )
        return f"{col + 1}{row_label}"

    @staticmethod
    def adjacent(col: int, row: int, direction: int) -> tuple[int, int]:
        """
        See https://www.redblobgames.com/grids/hexagons/#neighbors-doubled

        direction is 0 to 5.

        >>> base = (2, 2)
        >>> [HexGrid.adjacent(*base, d) for d in range(6)]
        [(3, 3), (3, 1), (2, 0), (1, 1), (1, 3), (2, 4)]
        >>> [HexGrid.cell_name(*HexGrid.adjacent(*base, d)) for d in range(6)]
        ['4D', '4B', '3A', '2B', '2D', '3E']
        """
        doubleheight_directions = [
            (+1, +1),
            (+1, -1),
            (0, -2),
            (-1, -1),
            (-1, +1),
            (0, +2),
        ]
        x_d, y_d = doubleheight_directions[direction]
        return col + x_d, row + y_d

    @cache
    def edge(self, x: int, y: int) -> bool:
        """
        On the outside edge?

        >>> hg = HexGrid(4)

        # Row numbers is double, but alternating grid means there's only really 4 rows.
        >>> hg.rows
        8

        # Columns defines the width in a square space
        >>> hg.columns
        4

        >>> hg.edge(0, 0)
        True
        >>> hg.edge(1, 3)
        False
        >>> hg.edge(4, 4)
        False
        >>> hg.edge(3, 7)
        True
        """
        left_right = x == 0 or x == self.columns - 1
        top_bottom = (
            (y == 0 or y == self.rows - 2)
            if x % 2 == 0
            else (y == 1 or y == self.rows - 1)
        )
        return top_bottom or left_right

    @cache
    def within(self, x: int, y: int) -> bool:
        """
        Within the hexgrid generally?

        >>> hg = HexGrid(4)
        >>> hg.within(0, 0)
        True
        >>> hg.within(-1, 3)
        False
        >>> hg.within(3, 7)
        True
        >>> hg.within(4, 8)
        False
        """
        left_right = 0 <= x <= self.columns - 1
        top_bottom = (
            (0 <= y <= self.rows - 2) if x % 2 == 0 else (1 <= y <= self.rows - 1)
        )
        inside = top_bottom and left_right
        # print(f"within({x}, {y}) -> {inside}")
        return inside


### 2. Terrain


class City:
    """
    A central "location" surrounded by a "domain".

    >>> hg=HexGrid(4)
    >>> c = City(hg, 'test', "tab:red")
    >>> c.name
    'test'
    >>> c.city_color
    '#d62728'
    >>> c.terrain_color
    '#e26161'
    >>> c.place(2, 2)
    >>> c.location
    (2, 2)
    >>> c.domain
    {(2, 4), (3, 1), (1, 1), (2, 0), (3, 3), (1, 3)}
    >>> repr(c)
    'test-3C'
    >>> (3, 3) in c.occupies()
    True
    >>> (4, 4) in c.occupies()
    False
    >>> sorted(c.border())
    [(0, 0), (0, 2), (0, 4), (1, -1), (1, 5), (2, -2), (2, 2), (2, 6), (3, -1), (3, 5), (4, 0), (4, 2), (4, 4)]
    """

    def __init__(self, hexgrid: HexGrid, name: str, color: str) -> None:
        self.hg = hexgrid
        self.name = name
        shift = 0.30  # 30% lighter.
        rgb = mcolors.to_rgb(mcolors.get_named_colors_mapping()[color])
        self.city_color = mcolors.to_hex(rgb)
        self.terrain_color = mcolors.to_hex(
            mcolors.hsv_to_rgb(
                mcolors.rgb_to_hsv(rgb) * [1.0, (1 - shift), (1 - shift)]
                + [0.0, 0.0, shift]
            )
        )
        self.location: tuple[int, int] | None = None
        self.domain: set[tuple[int, int]] = set()

    def __repr__(self):
        return f"{self.name}-{self.hg.cell_name(*self.location)}"

    __str__ = __repr__

    def place(self, x: int, y: int) -> None:
        self.location = (x, y)
        self.domain = {self.hg.adjacent(x, y, d) for d in range(6)}

    def add(self, x: int, y: int) -> None:
        self.domain.add((x, y))

    def occupies(self) -> set[tuple[int, int]]:
        return set(self.domain) | {self.location}

    def border(self) -> set[tuple[int, int]]:
        """All cell(s) adjacent to the city's domain"""
        # candidates = set()
        # for d in self.domain:
        #    candidates |= set(self.hg.adjacent(*d, dir) for dir in range(6))
        candidates = set(
            self.hg.adjacent(*d, dir) for d in self.domain for dir in range(6)
        )
        final_locations = candidates - set(self.domain)
        return final_locations


class Empire:
    """
    A collection of Cities.

    >>> hg = HexGrid(4)
    >>> e = Empire(hg)
    >>> c = City(hg, 'test', "tab:blue")
    >>> random.seed(42)
    >>> e.add_city(c)
    >>> sorted(e.occupied())
    [(1, 1), (1, 3), (2, 0), (2, 2), (2, 4), (3, 1), (3, 3)]
    """

    def __init__(self, hexgrid):
        self.hg = hexgrid
        self.cities = []

    def add_city(self, city: City) -> None:
        x, y = self.hg.random()
        while self.hg.edge(x, y):
            x, y = self.hg.random()
        while not self.hg.edge(x, y) and (x, y) in {c.location for c in self.cities}:
            x, y = self.hg.random()
        city.place(x, y)
        self.cities.append(city)

    def occupied(self) -> set[tuple[int, int]]:
        occ = set()
        for c in self.cities:
            occ.add(c.location)
            occ |= set(c.domain)
        return occ


COLORS = [
    "tab:blue",
    "tab:orange",
    "tab:green",
    "tab:red",
    "tab:purple",
    "tab:brown",
    "tab:pink",
    "tab:gray",
    "tab:olive",
    "tab:cyan",
]


def generate(
    hexgrid: HexGrid, seed: int, cities: int = 5, generations: int = 48, fill: int = 1
) -> Iterator[Empire]:
    """Build the Empire."""

    random.seed(seed)
    empire = Empire(hexgrid)

    # Plant the initial cities.
    # NOTE -- during this phase, occupied hexes don't count: cities can be adjacent.
    for i in range(cities):
        _, name = COLORS[i].split(":")
        c = City(hexgrid, name, COLORS[i])
        empire.add_city(c)

    # Initial
    yield empire

    # Expand each city through 48 adjacent cells. (Why 48? 48*5=240, grid is 18x14 = 252, 95% is the target
    # Inefficient algorithm recomputes border - occupied each time. Should simply add the new to city and occupied.
    for i in range(generations):
        # print(f"Generation {i}")
        occupied = empire.occupied()
        for c in empire.cities:
            expansion = c.border()
            expansion -= occupied
            if expansion:
                new = random.choice(list(expansion))
                if hexgrid.within(*new):
                    # print(f"Expand {c} to {new}")
                    c.add(*new)
                    occupied |= {new}
            else:
                pass
                # print(f"No Expansion for {c}")
        yield empire

    for i in range(fill):
        # Fill holes, eliminating "disputed" territories.
        holes = set(hexgrid.all())  # Refactor into Empire class
        for c in empire.cities:
            holes -= c.occupies()

        for h in holes:
            # print(f"\nfilling hole {hexgrid.cell_name(*h)}")
            neighbors = []
            for c in empire.cities:
                adjacent = [
                    d for d in range(6) if hexgrid.adjacent(*h, d) in c.occupies()
                ]
                if len(adjacent) == 6:
                    neighbors.append((c, len(adjacent)))
                else:
                    # Partial Coverage
                    neighbors.append((c, len(adjacent)))

            # Hole is (almost) fully surrounded...
            if sum(cells for city, cells in neighbors) >= 5:
                # May be some dispute here, we resolve it with a random choice.
                # TODO: Disputes get blended color and a fill pattern.
                assigned_city = random.choice(
                    [city for city, cells in neighbors if cells != 0]
                )
                assigned_city.add(*h)
            else:
                # Incomplete surround. (May be two adjacent holes.)
                # report = [f"{city!r} {cells}" for city, cells in partial if cells != 0]
                # print(f"Multi-Surround {hexgrid.cell_name(*h)}:  {', '.join(report)}")
                pass

        yield empire


### 3. Graphics


class Drawing:
    def __init__(self, grid_height: int, title: str = "Empire Builder") -> None:
        self.r: float

    def to_screen_x_y(self, col: int, row: int) -> tuple[float, float]:
        x_o = self.r * 3 / 2 * col + self.r
        y_o = self.r * sqrt(3) / 2 * row + self.r
        return x_o, y_o

    @abc.abstractmethod
    def paint(self, col: int, row: int, fill: str) -> None: ...

    def city(self, city: City) -> None:
        # print(f"City {city.city_color} at {HexGrid.cell_name(*city.location)} = {city.location}")
        self.paint(*city.location, fill=city.city_color)
        for terrain in city.domain:
            self.paint(*terrain, fill=city.terrain_color)

    def empire(self, empire: Empire) -> None:
        for c in empire.cities:
            self.city(c)

    def pause(self) -> None:
        pass

    @abc.abstractmethod
    def show(self) -> None: ...


class TurtleDrawing(Drawing):
    """
    While this (mostly) works, it is really slow.
    """

    def __init__(self, grid: HexGrid, title: str = "Empire Builder") -> None:
        self.tg = turtle.Turtle()
        screen = self.tg.getscreen()
        screen.title(title)
        w_screen, h_screen = screen.screensize()

        f_r = h_screen / grid.rows
        self.r = round(f_r / sqrt(3), 4)
        ax_w = 2 * grid.columns * self.r
        ax_h = grid.rows * sqrt(3) * self.r / 2  # Interleaved.

        coordinates = [-self.r / 2, -self.r / 2, ax_w, ax_w]
        screen.setworldcoordinates(*coordinates)
        screen.delay(None)
        self.tg.degrees()
        self.tg.speed(0)
        self.tg.hideturtle()

    def paint(self, col: int, row: int, fill: str) -> None:
        """
        Draw a hex.
        Expect E-facing as 0°. Turn Left to go around.
        Assumes X is offset by r/2 so the 0, 0 origin is visible.
        """
        x_o = self.r * 3 / 2 * col + self.r
        y_o = self.r * sqrt(3) / 2 * row + self.r
        # self.tg.teleport(x_o, y_o)  # 3.12
        self.tg.penup()
        self.tg.goto(x_o, y_o)
        self.tg.pendown()

        # Begin_poly
        self.tg.setheading(90.0)
        if fill:
            self.tg.fillcolor(fill)
            self.tg.begin_fill()
        self.tg.pencolor("black")
        for i in range(6):
            self.tg.forward(self.r)
            self.tg.left(60)
        if fill:
            self.tg.end_fill()
        # End_Poly

        label = HexGrid.cell_name(col, row)

        x = self.r * 3 / 2 * col
        y = self.r * sqrt(3) / 2 * row

        # Adjust for font height and label size.
        # self.tg.teleport(x + self.r, y + self.r/2) # 3.12
        self.tg.penup()
        self.tg.goto(x + 3 * self.r / 2, y + self.r)
        self.tg.pendown()
        self.tg.pencolor("gray")
        self.tg.write(label, align="center")

    def show(self) -> None:
        self.tg.screen.mainloop()  # Python 3.12 has done()


class PyPlotDrawing(Drawing):
    """
    Draw using matplotlib.pyplot.

    """

    def __init__(self, grid: HexGrid, title: str = "Empire Builder") -> None:
        self.fig = plt.figure(title, figsize=(4.0, 4.0), layout=None)

        # Seems to look right...
        h_screen = self.fig.get_figheight() / 2.25

        # Refactor the computations into superclass
        f_r = h_screen / grid.rows
        self.r = round(f_r / sqrt(3), 4)
        ax_w = 2 * grid.columns * self.r
        ax_h = grid.rows * sqrt(3) * self.r / 2  # Interleaved.

        coordinates = (-self.r / 2, -self.r / 2, ax_w, ax_w)

        self.ax = self.fig.add_axes(coordinates, frameon=False, aspect=1)
        self.ax.set_axis_off()

        self.fill_colors: dict[tuple[int, int], str] = {}
        self.cells: dict[tuple[int, int], list[Polygon]] = {}
        self.borders: dict[tuple[int, int], list[Line2D]] = {}
        self.labels: dict[tuple[int, int], Artist] = {}

        for col, row in grid.all():
            path = self.hexpath(self.r, col, row)
            x = [pt[0] for pt in path]
            y = [pt[1] for pt in path]
            label = grid.cell_name(col, row)
            self.fill_colors[col, row] = "w"
            self.cells[col, row] = self.ax.fill(x, y, self.fill_colors[col, row])
            self.borders[col, row] = self.ax.plot(x, y, "-k", lw=0.75)
            lab_x = self.r * 3 / 2 * col
            lan_y = self.r * sqrt(3) / 2 * row
            self.labels[col, row] = self.ax.text(
                lab_x + self.r,
                lan_y + self.r / 2,
                label,
                family="sans-serif",
                size="x-small",
                color="tab:gray",
                horizontalalignment="center",
            )

        plt.ion()

    @staticmethod
    def hexpath(r: float, col: int, row: int) -> list[tuple[float, float]]:
        """
        Coordinates of hex vertices.

        >>> PyPlotDrawing.hexpath(1.0, 2, 2)
        [(5.0, 2.73205), (4.5, 3.59808), (3.5, 3.59808), (3.0, 2.73205), (3.5, 1.86603), (4.5, 1.86603), (5.0, 2.73205)]
        """
        x_o = r * 3 / 2 * col + r
        y_o = r * sqrt(3) / 2 * row + r
        path = []
        for side in range(0, 6):
            theta = radians(60 * side)
            x = round(cos(theta) * r + x_o, 5)
            y = round(sin(theta) * r + y_o, 5)
            path.append((x, y))
        path.append(path[0])
        return path

    def paint(self, col: int, row: int, fill: str) -> None:
        """
        Update a hex's fill color.
        """
        self.fill_colors[col, row] = fill
        for a in self.cells[col, row]:
            a.set(fill=True, color=fill)

    def city(self, city: City) -> None:
        # print(f"City {city.city_color} at {HexGrid.cell_name(*city.location)} = {city.location}")
        self.paint(*city.location, fill=city.city_color)
        for terrain in city.domain:
            self.paint(*terrain, fill=city.terrain_color)

    def empire(self, empire: Empire) -> None:
        for c in empire.cities:
            self.city(c)

    def pause(self) -> None:
        plt.pause(0.03)

    def show(self) -> None:
        plt.ioff()
        plt.show()


### 4. Applications


# Option 1 -- Animated.


def show_empire_1(drawing: Drawing, generator: Iterable[Empire]) -> Empire:
    empire_iter = iter(generator)
    e_0 = next(empire_iter)
    drawing.empire(e_0)
    for empire in empire_iter:
        drawing.empire(empire)
        drawing.pause()
    return empire


# Option 2 -- No animation.


def show_empire_2(drawing: Drawing, generator: Iterable[Empire]) -> Empire:
    sequence = list(generator)
    empire = sequence[-1]

    drawing.empire(empire)
    return empire


### 5. Test, Demo, Main


@task()
def test(c, verbose=False) -> None:
    import doctest

    doctest.testmod(verbose=verbose)


@task(test)
def demo(c) -> None:
    hg = HexGrid(18)
    drawing = PyPlotDrawing(hg)

    c = City(hg, "Red", "tab:red")
    x, y = hg.random()
    c.place(x, y)
    drawing.city(c)
    drawing.show()


@task(test)
def empire(
    c,
    animation: bool = True,
    seed: int | None = 12991971503914480054,
    cities: int = 5,
    generations: int = 48,
    fill: int = 1,
) -> None:
    if not seed:
        seed = reduce(lambda a, b: a * 256 + b, os.urandom(4))
    if cities > 10:
        raise ValueError("Cities must be between 1 and 10")
    print(
        f"python {Path(__file__).name} empire --seed={seed} --cities={cities} --generations={generations}"
    )
    hexgrid = HexGrid(18)
    drawing = PyPlotDrawing(hexgrid, f"Empire {seed}")
    # drawing = TurtleDrawing(hexgrid)

    generator = generate(
        hexgrid, seed, cities=cities, generations=generations, fill=fill
    )
    if animation:
        show_empire_1(drawing, generator)
    else:
        show_empire_2(drawing, generator)
    drawing.show()


if __name__ == "__main__":
    tasks = Collection()
    tasks.add_task(test)
    tasks.add_task(demo)
    tasks.add_task(empire)

    program = Program(namespace=tasks, version="1.0")

    program.run()
