"""Plot Points.

Storytelling Notes
==================

The three-act hero's journey involves a departure, an initiation,
and a return. Something must be lost for something to be gained.


Output
======

The default is an HTML page. This can be saved and rendered
with a browser to see the images.

::

    python plot.py >story_1.html && open story_1.html

The -t option produces a text-only summary.

Images
======

See this site:

http://www.sacred-texts.com/tarot/xr

There's a fairly complex naming scheme to translate cards to images.

-   Fool: http://www.sacred-texts.com/tarot/pkt/img/ar00.jpg

-   World: http://www.sacred-texts.com/tarot/pkt/img/ar21.jpg

-   two cups: http://www.sacred-texts.com/tarot/pkt/img/cu02.jpg

-   ace cups: http://www.sacred-texts.com/tarot/pkt/img/cuac.jpg

-   king cups: http://www.sacred-texts.com/tarot/pkt/img/cuki.jpg

-   knight cups: http://www.sacred-texts.com/tarot/pkt/img/cukn.jpg

-   page cups: http://www.sacred-texts.com/tarot/pkt/img/cupa.jpg

-   queen cups: http://www.sacred-texts.com/tarot/pkt/img/cuqu.jpg

We can summarize the rules like this:

::

    cups = "cu"
    pentacles = "pe"
    swords = "sw"
    wands = "wa"

There are two versions:

-   Color Path http://www.sacred-texts.com/tarot/pkt/img/wa07.jpg

-   B&W Path   http://www.sacred-texts.com/tarot/pkt/tn/wa07.jpg

Images are 300 x 528 at the source. We scale them to width=75px x height=132px.
This means the transformation involves a shift by 32.5px

Dependencies
============

Jinja2 is used to fill in the HTML templates.
Rich provides a rich display for the text.

Notes
=====

In a narrow, technical sense the five-card layout has two cards placed over
each other.  We just mush them into a single cell.

"""
import argparse
from enum import Enum
import json
from pathlib import Path
import random
import sys
from textwrap import dedent, indent
from typing import Any, NamedTuple, Iterator, Union, TextIO

from jinja2 import Environment, DictLoader, select_autoescape
from rich import print, box
from rich.console import Console, ConsoleOptions, RenderResult
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

class Minor(NamedTuple):
    """A card in the "minor arcana" of a Tarot deck.

    >>> m = Minor("Page", "Swords", "Spy")
    >>> m.name
    'Page Swords'
    >>> m.url
    'http://www.sacred-texts.com/tarot/pkt/img/swpa.jpg'
    """

    rank: str  #: Rank of the card ("Ace" to "King")
    suit: str  #: Suit of the card: "Wands", "Swords", "Cups", "Pentacles"
    text: str  #: A summary of the meaning of the card

    def __str__(self):
        return f"{self.rank} {self.suit}: {self.text}"

    @property
    def name(self):
        """The rank and suit name of this card."""
        return f"{self.rank} {self.suit}"

    @property
    def url(self):
        """The URL for an image of this card."""
        s = {"Wands": "wa", "Swords": "sw", "Cups": "cu", "Pentacles": "pe"}[self.suit]
        r = {
            "Ace": "ac",
            "Two": "02",
            "Three": "03",
            "Four": "04",
            "Five": "05",
            "Six": "06",
            "Seven": "07",
            "Eight": "08",
            "Nine": "09",
            "Ten": "10",
            "Page": "pa",
            "Knight": "kn",
            "Queen": "qu",
            "King": "ki",
        }[self.rank]
        return f"http://www.sacred-texts.com/tarot/pkt/img/{s}{r}.jpg"


class Major(NamedTuple):
    """A card in the "major arcana" of a Tarot deck.

    >>> m = Major("XIX", "Sun", "Achievement")
    >>> m.name
    'XIX Sun'
    >>> m.url
    'http://www.sacred-texts.com/tarot/pkt/img/ar19.jpg'

    >>> v = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
    >>> for n, r in enumerate(v):
    ...     c = Major(r, str(n), str(n))
    ...     assert c.rank_int == n, f"{c.name!r}: {c.rank_int} != {n}"
    """

    rank: str  #: Rank is a roman numeral from "I" to "XXI" or "0"
    image: str  #: Image is the name of the card
    text: str  #: A summary of the meaning of the card

    def __str__(self):
        return f"{self.rank} {self.image}: {self.text}"

    @property
    def name(self):
        """The rank and image name of this card."""
        return f"{self.rank} {self.image}"

    @property
    def rank_int(self):
        if self.rank == "0":
            r = 0
        else:
            rank = self.rank
            reverses = {"IX": 9, "IV": 4, "IL": 49, "VL": 45, "XL": 40}
            singles = {"L": 50, "X": 10, "V": 5, "I": 1}
            n = []
            for rv_pat, value in reverses.items():
                if rv_pat in rank:
                    rank = rank.replace(rv_pat, "", 1)
                    n.append(value)
            for s_pat, value in singles.items():
                while s_pat in rank:
                    rank = rank.replace(s_pat, "", 1)
                    n.append(value)
            assert rank == "", f"Invalid rank {self.rank}"
            r = sum(n)
        return r

    @property
    def url(self):
        """The URL for an image of this card."""
        return f"http://www.sacred-texts.com/tarot/pkt/img/ar{self.rank_int:02d}.jpg"


Card = Union[Major, Minor]



minor_raw = [
    {"rank": "Ace", "suit": "Wands", "text": "Gift"},
    {"rank": "Ace", "suit": "Swords", "text": "Triumph through battle"},
    {"rank": "Ace", "suit": "Cups", "text": "Abundance (food, 1st aid)"},
    {"rank": "Ace", "suit": "Pentacles", "text": "Wealth"},
    {"rank": "Two", "suit": "Wands", "text": "Lord of a manor"},
    {"rank": "Two", "suit": "Swords", "text": "Stalemate"},
    {"rank": "Two", "suit": "Cups", "text": "Partnership"},
    {"rank": "Two", "suit": "Pentacles", "text": "Sudden change for better"},
    {"rank": "Three", "suit": "Wands", "text": "Merchant"},
    {"rank": "Three", "suit": "Swords", "text": "Loss, Separation"},
    {"rank": "Three", "suit": "Cups", "text": "Conclusion of strife"},
    {"rank": "Three", "suit": "Pentacles", "text": "Mastery of construction"},
    {"rank": "Four", "suit": "Wands", "text": "Refuge, haven"},
    {"rank": "Four", "suit": "Swords", "text": "Rest, exile"},
    {"rank": "Four", "suit": "Cups", "text": "Hesitancy"},
    {"rank": "Four", "suit": "Pentacles", "text": "Miser"},
    {"rank": "Five", "suit": "Wands", "text": "Battle with aid"},
    {"rank": "Five", "suit": "Swords", "text": "Conquest or threat"},
    {"rank": "Five", "suit": "Cups", "text": "Loss or gain not to expectation"},
    {"rank": "Five", "suit": "Pentacles", "text": "Lost from truth"},
    {"rank": "Six", "suit": "Wands", "text": "Victory through conquest"},
    {"rank": "Six", "suit": "Swords", "text": "Represent self to others"},
    {"rank": "Six", "suit": "Cups", "text": "Vanished past (treasure?)"},
    {"rank": "Six", "suit": "Pentacles", "text": "Charity to henchmen"},
    {"rank": "Seven", "suit": "Wands", "text": "Battle without aid"},
    {"rank": "Seven", "suit": "Swords", "text": "Partial success or loss"},
    {"rank": "Seven", "suit": "Cups", "text": "Scattered force"},
    {"rank": "Seven", "suit": "Pentacles", "text": "Long hard labor"},
    {"rank": "Eight", "suit": "Wands", "text": "Journey"},
    {"rank": "Eight", "suit": "Swords", "text": "Wasted Energy"},
    {"rank": "Eight", "suit": "Cups", "text": "Abandon course"},
    {"rank": "Eight", "suit": "Pentacles", "text": "Prepare for merchant"},
    {"rank": "Nine", "suit": "Wands", "text": "Strength in reserve"},
    {"rank": "Nine", "suit": "Swords", "text": "Misery, doubt"},
    {"rank": "Nine", "suit": "Cups", "text": "Material Success"},
    {"rank": "Nine", "suit": "Pentacles", "text": "Land, accomplishment"},
    {"rank": "Ten", "suit": "Wands", "text": "Uniwse use of power"},
    {"rank": "Ten", "suit": "Swords", "text": "Sudden mis-fortune"},
    {"rank": "Ten", "suit": "Cups", "text": "Bounty to come"},
    {"rank": "Ten", "suit": "Pentacles", "text": "Land, wealth, Keep"},
    {"rank": "Page", "suit": "Wands", "text": "Hireling, messenger"},
    {"rank": "Page", "suit": "Swords", "text": "Spy"},
    {"rank": "Page", "suit": "Cups", "text": "Henchmen w/ information"},
    {"rank": "Page", "suit": "Pentacles", "text": "Respect for information"},
    {"rank": "Knight", "suit": "Wands", "text": "Discord w/ hireling; travel, change"},
    {"rank": "Knight", "suit": "Swords", "text": "Sudden Destruction"},
    {"rank": "Knight", "suit": "Cups", "text": "Bearer of boon"},
    {"rank": "Knight", "suit": "Pentacles", "text": "Utility, competence"},
    {"rank": "Queen", "suit": "Wands", "text": "Friendly lady"},
    {"rank": "Queen", "suit": "Swords", "text": "Keen-eyed decision"},
    {"rank": "Queen", "suit": "Cups", "text": "Vision/dream"},
    {"rank": "Queen", "suit": "Pentacles", "text": "Talented aid"},
    {"rank": "King", "suit": "Wands", "text": "Favor from overlord"},
    {"rank": "King", "suit": "Swords", "text": "Wise man, Good advice"},
    {"rank": "King", "suit": "Cups", "text": "Generosity"},
    {"rank": "King", "suit": "Pentacles", "text": "Lord of merchants"},
]
major_raw = [
    {
        "rank": "0",
        "image": "Fool",
        "text": "Choose correctly or fail.  Drunk, drugged, lost, confused",
    },
    {
        "rank": "I",
        "image": "Magician",
        "text": "Skilled use of power, diplomatic agreement",
    },
    {
        "rank": "II",
        "image": "High Priestess",
        "text": "Veiled enigma (unseen enemies??, hidden item??), Information, Secrets, wisdom, science",
    },
    {
        "rank": "III",
        "image": "Empress",
        "text": "Luxury, creativity (trap??), action, adventure, risk",
    },
    {
        "rank": "IV",
        "image": "Emperor",
        "text": "Intelligent domination, stability, power, success, control",
    },
    {"rank": "V", "image": "Hierophant", "text": "Social approval, servitude, capture"},
    {
        "rank": "VI",
        "image": "Lovers",
        "text": "Choice between different benefits, misguided attraction",
    },
    {
        "rank": "VII",
        "image": "Chariot",
        "text": "Battle and conquest, war, vengeance, riot, dispute",
    },
    {
        "rank": "VIII",
        "image": "Strength",
        "text": "Will & discipline over impulse & lust, power, courage, magnanimity",
    },
    {
        "rank": "IX",
        "image": "Hermit",
        "text": "Council, Wisdom leading, treason, rouguery, corruption",
    },
    {
        "rank": "X",
        "image": "Fortune",
        "text": "Good luck in spite of monsters (4 of 'em!!), destiny, karma, fate",
    },
    {
        "rank": "XI",
        "image": "Justice",
        "text": "Balanced activity, equity, righteousness, probity, law",
    },
    {
        "rank": "XII",
        "image": "Hanged man",
        "text": "Reversal, Sacrifice, bad luck, intuition, divination",
    },
    {"rank": "XIII", "image": "Death", "text": "Destruction, followed by change"},
    {
        "rank": "XIV",
        "image": "Temperance",
        "text": "Balance, economy, frugality, gathering, keeping, reducing",
    },
    {
        "rank": "XV",
        "image": "Devil",
        "text": "Illness, slavery (poison??), ravage, violence, force",
    },
    {
        "rank": "XVI",
        "image": "Tower",
        "text": "Overthrow, catastrophe, adversity, deception, ruin, prison",
    },
    {
        "rank": "XVII",
        "image": "Star",
        "text": "Hope, inspiration (out of darkness), loss, theft, privation",
    },
    {
        "rank": "XVIII",
        "image": "Moon",
        "text": "Dreams, visions, secret perils (traps??)",
    },
    {"rank": "XIX", "image": "Sun", "text": "Achievement, liberation, contentment"},
    {"rank": "XX", "image": "Judgement", "text": "Renewal, awakening"},
    {"rank": "XXI", "image": "World", "text": "Reward, flight, escape, emigration"},
]


def make_deck(minor: list[Card], major: list[Card]) -> list[Card]:
    minor_card: list[Card] = [Minor(**r) for r in minor]
    major_card: list[Card] = [Major(**r) for r in major]
    return minor_card + major_card


class PrepositionDetail(NamedTuple):
    """
    One of the positions in the spread.
    """

    role: str  #: The role of this card
    description: str  #: A description for the role
    row: int  #: Row number in the Spread, 0 is the top
    col: int  #: Column number, In the range 0-11


class Tarot_1(PrepositionDetail, Enum):
    """The positions in a 6-card spread.

    >>> Tarot_1.need.value.role
    'NEED'
    >>> Tarot_1.need.value.description
    'what the hero must gain to replace the lie'

    Layout:

    +----------+----------+---------+
    | col=0    | col=4    | col=8   |
    +----------+----------+---------+
    |          | need     |         |
    |          |          |         |
    |          |          |         |
    +----------+----------+---------+
    | Coming   | To do    | Going   |
    | From     |          | To      |
    |          |          |         |
    +          +----------+         +
    |          | Overcome |         |
    |          |          |         |
    |          |          |         |
    +----------+----------+---------+
    |          | avoid    |         |
    |          |          |         |
    |          |          |         |
    +----------+----------+---------+

    The ToDo and Overcome cards are traditionally laid on top of each other.
    This is awkward to display. We have two choices.

    -   Subdivide the cell at row 1, col 4 to be a sub-layout with two cards.
        This is a TODO item.

    -   Treat other cells ad vertical spans, and hope it's visually useful.

    """

    do = PrepositionDetail("TO DO", "character goal", row=1, col=4)

    # Coming From is a background that embraces the lie.
    comingfrom = PrepositionDetail("COMING FROM", "background, embracing the lie", row=1, col=0)

    # Overcome is the superficial barrier blocking the “want”.
    overcome = PrepositionDetail("TO OVERCOME", "obstacle, person, god, or curse blocking the want", row=2, col=4)

    # Going To is the “want”: the tangible, but unhelpful thing.
    goingto = PrepositionDetail("GOING TO", "what the character wants, tangible but unhelpful", row=1, col=8)

    # Avoiding is the lie to overcome — the foundational problem.
    avoid = PrepositionDetail("AVOID", "the lie the hero must discard", row=3, col=4)

    # Need/Embrace is the replacement for the lie, the real thing the character
    # needs. This may lead to a rising or falling or flat character arc
    need = PrepositionDetail("NEED", "what the hero must gain to replace the lie", row=0, col=4)


class Tarot_Simple(PrepositionDetail, Enum):
    """The positions in a 5-card spread.

    See https://www.eadeverell.com/the-one-page-novel-plot-formula/

    In Plot Order:

    1. RESOLUTION. Goal. Actual Going To.
    2. STASIS. Obstacle. The Lie.
    3. SHIFT. Path. A thing MC will learn; changes path to DEFEAT (and then POWER).
    4. TRIGGER. Path. False Hope. Setup for BOLT and SHIFT
    5. QUEST. Path. Doomed to DEFEAT, but the DEFEAT leads to POWER
    6. POWER. Goal. Another thing we will learn; completes transformation for RESOLUTION,
    7. BOLT. Obstacle. A surprise attack, a set-back, or a diversion breaking the QUEST.
    8. DEFEAT. Obstacle. Actual Coming From. Recognizing this ends the QUEST

    In Story Order:

    2. STASIS. The Lie.
    4. TRIGGER. False Hope.
    5. QUEST.
    7. BOLT.
    3. SHIFT.
    8. DEFEAT. Coming From.
    6. POWER.
    1. RESOLUTION. Going To.

    >>> Tarot_Simple.character.value.role
    'CHARACTER'
    >>> Tarot_Simple.character.value.description
    'the MC synopsis or archetype'

    Layout:

    +----------+----------+---------+
    | col=0    | col=4    | col=8   |
    +----------+----------+---------+
    |          | False    |         |
    |          | Hope     |         |
    |          |          |         |
    +----------+----------+---------+
    | Coming   | MC       | Going   |
    | From     |          | To      |
    |          |          |         |
    +----------+----------+---------+
    |          | The Lie  |         |
    |          |          |         |
    |          |          |         |
    +----------+----------+---------+

    """

    character = PrepositionDetail("CHARACTER", "the MC synopsis or archetype", row=1, col=4)

    # Going To is the actual goal, the character truly needs to do.
    goingTo = PrepositionDetail("GOING TO", "actual objective", row=1, col=8)

    # Coming From is the actual background, not acknowledged by the character.
    comingFrom = PrepositionDetail("COMING FROM", "actual history", row=1, col=0)

    # The Lie is the the character's past that is holding them back.
    theLie = PrepositionDetail("THE LIE", "history/context acknowledged (the lie)", row=2, col=4)

    # False Hope is the a goal based on the lie.
    falseHope = PrepositionDetail("FALSE HOPE", "what the character thinks they want, colored by the lie", row=0, col=4)


class Tarot_ShortStory(PrepositionDetail, Enum):
    """Some positions in a 7-card spread.

    1. A Character
    2. in a Situation
    3. with a Problem
    4. tries to solve the problem
    5. but fails, making it worse
    6. they try to solve the new problem
    7. and the consequence is not what they expected

    Layout:

    +----------+----------+---------+
    | col=0    | col=4    | col=8   |
    +----------+----------+---------+
    |          | Problem  |         |
    |          |          |         |
    +----------+----------+---------+
    | Try 1    | Character| Worse   |
    +----------+----------+---------+
    | Try 2    |          | Outcome |
    +----------+----------+---------+
    |          | Situation|         |
    |          |          |         |
    |          |          |         |
    +----------+----------+---------+

    """

    character = PrepositionDetail("CHARACTER", "A Character...", row=1, col=4)

    situation = PrepositionDetail("SITUATION", "In a Situation...", row=3, col=4)

    goingTo = PrepositionDetail("PROBLEM", "Has a Problem", row=0, col=4)

    try_1 = PrepositionDetail("TRY1", "They try to solve it", row=1, col=0)

    fail_1 = PrepositionDetail("FAIL1", "and make it worse", row=1, col=8)

    try_2 = PrepositionDetail("TRY2", "They try to solve the new problem", row=2, col=0)

    fail_2 = PrepositionDetail("FAIL2", "the outcome is not what they expected", row=2, col=8)



Spread = PrepositionDetail


class Story(dict[PrepositionDetail, Card]):
    """A mapping from a Spread's enumeration of ``PrepositionDetail`` to a ``Card``.

    >>> d = [
    ...    Minor("Ace", "Swords", "one"),
    ...    Minor("Two", "Swords", "two"),
    ...    Minor("Three", "Swords", "three"),
    ...    Minor("Four", "Swords", "four"),
    ...    Minor("Five", "Swords", "five"),
    ...    Minor("Six", "Swords", "six"),
    ...    Minor("Seven", "Swords", "not used"),
    ... ]
    >>> s = Story.build(Tarot_1, *d[:6])
    >>> str(s[Tarot_1.need])
    'Six Swords: six'
    >>> s[Tarot_1.need]
    Minor(rank='Six', suit='Swords', text='six')
    >>> for l in s.text():
    ...     print(l)
    TO DO character goal
    -   Ace Swords: one
    <BLANKLINE>
    COMING FROM background, embracing the lie
    -   Two Swords: two
    <BLANKLINE>
    TO OVERCOME obstacle, person, god, or curse blocking the want
    -   Three Swords: three
    <BLANKLINE>
    GOING TO what the character wants, tangible but unhelpful
    -   Four Swords: four
    <BLANKLINE>
    AVOID the lie the hero must discard
    -   Five Swords: five
    <BLANKLINE>
    NEED what the hero must gain to replace the lie
    -   Six Swords: six
    <BLANKLINE>
    >>> for r in s.rc_iter():
    ...     print([(w, o, p.row, p.col) for w, o, p in r])
    [(4, 4, 0, 4)]
    [(4, None, 1, 0), (4, None, 1, 4), (4, None, 1, 8)]
    [(4, 4, 2, 4)]
    [(4, 4, 3, 4)]
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def build(cls, spread: Spread, *cards: Card) -> "Story":
        assert len(cards) == len(spread), f"Need {len(spread)} cards"
        story = Story({p: cards[n] for n, p in enumerate(spread)})
        return story

    def rc_iter(self) -> Iterator[list[tuple[int, int | None, PrepositionDetail]]]:
        """
        Emit rows as lists of (width, offset, PrepositionDetail) triples.
        We compute the widths based on the following cell position.
        This fits with bootstrap CSS column definitions.

        :yields: list of tuple with (width, optional offset, PrepositionDetail) for each column of a row

        TODO: Discover when multiple cards are in a single cell, forcing the display templates
            to subdivide the cell into sub-rows.
        """

        def widths(row: list[PrepositionDetail]) -> Iterator[tuple[int, PrepositionDetail]]:
            """Compute widths. Yield col width and row detail as a pair"""
            cols = [c.col for c in row] + [12]
            for i in range(len(row)):
                yield cols[i+1] - cols[i], row[i]

        def standardized(standard: int, row: list[tuple[int, PrepositionDetail]]) -> Iterator[tuple[int, int|None, PrepositionDetail]]:
            """Standardizes widths, provides offsets where needed."""
            offset = 0
            for w, detail in row:
                yield (standard, None if detail.col == offset else detail.col-offset, detail)
                offset = detail.col + standard

        # Build nested dicts with rows in the outer and columns in the inner
        cells = {r: {} for r in sorted({p.row for p in self})}
        for p in self:
            cells[p.row][p.col] = p
        # Regroup into lists of lists in sorted order.
        cards_by_row = [sorted(cells[row].values(), key=lambda p: (p.row, p.col)) for row in cells]
        # Extract the widths by subtracting column of card x from column of card x+1 (or 12 for the last card)
        width_detail_by_row = [list(widths(row)) for row in cards_by_row]
        # The minimum width becomes a standard width
        least = min(w for row in width_detail_by_row for w, d in row)
        # Apply the standard and compute offsets where needed.
        for row in width_detail_by_row:
            normalized = list(standardized(least, row))
            yield normalized

    def text(self):
        """A plain text view of the story as an enumeration of the cards."""
        return [
            f"{p.value.role} {p.value.description}\n-   {self[p]}\n"
            for p in self
        ]

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        for p in self:
            yield f"[bold]{p.value.role}[/bold] [italic]{p.value.description}[/italic]"
            yield indent(f"[bold]{self[p].name}[/bold]: {self[p].text}", prefix='    ')
            yield ""


def make_story(spread: Spread, deck: list[Card]) -> Story:
    """Build a Story from a Deck."""
    random.shuffle(deck)
    return Story.build(spread, *deck[:len(spread)])


BASE_PAGE = dedent("""
    {%-macro card(position, story_card, rotated=False)%}
    <div class="card">
      <div class="card-header"><p class="h4">{{position.value.role}}<p><p class="small">{{position.value.description}}</p></div>
      <img class="card-img-top{%if rotated%} rotated{%endif%}" style="max-width: 75px;" src="{{story_card.url}}" alt="{{story_card.name}}"/>
      <div class="card-body">
        <h4 class="card-title">{{story_card.name}}</h4>
        <p class="card-text">{{story_card.text}}</p>
      </div>
    </div>
    {%endmacro-%}
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <!-- Required meta tags -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
        <title>{%block title%}Tarot Plot Points{%endblock%}</title>

        <style>
        .rotated {transform: rotate(90deg) translateY(-32.5px);}
        </style>
      </head>
      <body>
        {%block body%}
        <h1>Hello, world!</h1>
        {%endblock%}

        <!-- Optional JavaScript; Separate Popper and Bootstrap JS -->
        <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.10.2/dist/umd/popper.min.js" integrity="sha384-7+zCNj/IqJ95wo16oMtfsKbZ9ccEh31eOz1HGyDuCQ6wgnyJNSYdrPa03rtR1zdB" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.min.js" integrity="sha384-QJHtvGhmr9XOIpI6YVutG+2QOK9T+ZnN4kzFN1RtK3zEFEIsxhlmWl5/YESvpZ13" crossorigin="anonymous"></script>
      </body>
    </html>
    """)

# TODO: When multiple cards are in a single cell, subdivide that cell into rows.]
# Also, rotate the second image in a cell with a {{card(..., rotated=True}}

STORY_PAGE = dedent("""
    {%extends "base_page.html"-%}
    {%-block title%}Tarot-based plot points{%endblock%}
    {%-block body%}
    <div class="container">

        <div class="row">
            {#Text Layout#}
            <div class="col-md-9 col-md-offset-2">
                <h1>The Essential Story</h1>
                <pre>{%for line in story.text()-%}
    {{line}}
    {%endfor-%}</pre>
            </div>
        </div>

        <div class="row">
            {#Image Layout#}
            <div class="col-md-9 col-md-offset-2">
                <h2>Images</h2>
                {%for row in story.rc_iter()%}
                <div class="row">
                    {# TODO: Split cells when multiple cards in a cell #}
                    {%for width, offset, col in row%}
                    <div class="col-md-{{width}} {%if offset%} offset-md-{{offset}}{%else%}{%endif%}">
                    {{card(col, story[col])}}
                    </div>
                    {%endfor%}
                </div>
                {%endfor%}
            </div>
        </div>
    </div>
    {%endblock%}
    """)


def make_page(story: Story, target: TextIO = sys.stdout) -> None:
    """Write an HTML page to represent the story."""
    template_map = {
            "base_page.html": BASE_PAGE,
            "story_page.html": STORY_PAGE,
    }
    env = Environment(
        loader=DictLoader(template_map),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("story_page.html")
    final_page = template.render(story=story)

    target.write(final_page)


def make_layout(story: Story) -> None:
    """Build a rich Layout object with the cards."""
    max_across = max(
        len(row) for row in story.rc_iter()
    )

    def rc_to_panel(story: Story) -> Iterator[Panel]:
        for row in story.rc_iter():
            splits = []
            for width, offset, detail in row:
                if offset:
                    # Empty space
                    splits.append(Panel("", box=box.MINIMAL, height=None))
                splits.append(
                    Panel(
                        renderable=Text.from_markup(f"\n[red]{story[detail]}[/red]\n"),
                        title=detail.description,
                        subtitle=detail.role,
                        border_style="bold",
                        box=box.HEAVY_EDGE,
                        height=None,
                    )
                )
            while len(splits) != max_across:
                splits.append(Panel("", box=box.MINIMAL, height=None))
            l = Layout()
            l.split_row(*splits)
            yield l

    layout = Layout()
    layout.split_column(
        *rc_to_panel(story)
    )
    print(layout)


def main(argv: list[str] = sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--text", action="store_true", default=False)
    parser.add_argument("-s", "--spread", action="store", choices=["7", "6", "5", "seven", "six", "five"], default="6")
    options = parser.parse_args(argv)

    tarot_cards = make_deck(minor_raw, major_raw)

    match options.spread:
        case "7" | "seven":
            spread = Tarot_ShortStory
        case "6" | "six":
            spread = Tarot_1
        case "5" | "five":
            spread = Tarot_Simple
        case _:
            sys.exit(f"spread value of {options.spread!r} is invalid")

    story = make_story(spread, tarot_cards)

    if options.text:
        print(story)
        make_layout(story)
    else:
        make_page(story)


if __name__ == "__main__":
    main()
