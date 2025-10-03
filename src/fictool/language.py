"""
ConLang Grammar and Lexicon.

See https://www.nltk.org/book/ch05.html for the Parts-of-Speech Tags

Also, see https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
for a more complete set.

See https://www.cis.upenn.edu/~bies/manuals/tagguide.pdf

Also https://universaldependencies.org/u/pos/all.html

The tricky part is -- of course -- the grammar.

Our goal is to move from a tagged English parse tree to the ConLang tree through a number of transformations.

Input
::

    (S (VP (TV kill) (NP (DET the) (N mage))))

In English, this Transitive Verb example doesn't have a subject only an object.
English permits ``S -> VP NP`` as well as more the more conventional ``S -> NP VP`` structures.

See https://ucrel.lancs.ac.uk/bnc2/bnc2guide.htm where VVI/VVZ is used for imperative.

The target ConLang in this implementation is ``VP NP NP``, ``VP NP PP``, ``VP NP PP NP PP`` kinds of things. Note the recursive
NP -> Det Nominal and Nominal -> Nominal Noun to permit constructing complicated relationships.

"go-Kill you the mage" sorts of constructs.
Present is the base form.
Imperative is a "go-" prefix.
Present participle ("-ing" in English) is a "now-" prefix.
Past ("-ed" in English) is a "did-" prefix.
No person conjugation. It's a separate word after the verb.

..  csv-table:: Verb Subcategories

    Symbol,	Meaning,	Example
    IV,	intransitive verb,	barked ``(VP -> IV Adj)``
    TV,	transitive verb,	saw a man ``(VP -> TV NP)``
    DatV,	dative verb,	gave a dog to a man ``(VP -> NP PP)``
    SV,	sentential verb,	said that a dog barked ``(V -> SV S)``

Generally, this example ConLang lacks Intransitive verbs. "did-Bark the dog at something."
"did-See myself the man." "did-Give the dog to a man." "did-Say the man did-Bark the dog at something."

Rules needed
============

- Pivot Declarative to VP first. ``(S (NP $n) (VP $v) $x) -> (S (VP $v) (NP $n) $x)``.
  Imperative ``(S (VP))`` left alone.
  Interrogative ``(S (Aux NP VP))``, ``(S (Wh-NP VP))``, ``(S (Wh-NP Aux NP VP))`` should also be swapped around to verb first.

- Adverbs are split out with a helper. ``(VP $x (ADVP (NP $y))) -> (VP $x (PP with (NP $y)))``.

- The Verb Subcategories rules, above.

- Apply Tense Prefix to base Verb's stem word. ``(VP (MD $m) (VP $v)) -> (VP ${f|prefix(m)}))`` rewrite verb root with mode prefix.

- Apply noun determiner suffix to nounds ``(NP (DET $d) (N $n)) -> (NP ${n|suffix(d)})``.

"""

import argparse
import bisect
from collections import defaultdict, deque
import csv
from enum import Enum
import hashlib
import io
import itertools
from pprint import pprint, pformat
import random
import re
import sys
from textwrap import dedent
from typing import NamedTuple, TypeVar, List, Tuple, Dict, Callable, Union

### Weighted Choices.

CT = TypeVar("CT")

def weighted_choice(source: List[Tuple[CT, int]]) -> CT:
    """Given [(string, int), ...] weighted strings, pick a string."""
    choices, weights = zip(*source)
    cumulative_dist = list(itertools.accumulate(weights))
    selection = random.random()*cumulative_dist[-1]
    return choices[bisect.bisect(cumulative_dist, selection)]

def test_weighted_choice_1() -> None:
    source = [('a', 1), ('b', 1), ('c', 1), ('d', 1)]
    random.seed(42)
    examples = [weighted_choice(source) for _ in range(1000)]
    assert examples[:10] == ['c', 'a', 'b', 'a', 'c', 'c', 'd', 'a', 'b', 'a']
    from collections import Counter
    distribution = Counter(examples)
    assert distribution.most_common() == [('c', 263), ('d', 257), ('b', 242), ('a', 238)]

def test_weighted_choice_2() -> None:
    source = [('a', 1), ('b', 2), ('c', 4), ('d', 8)]
    random.seed(42)
    examples = [weighted_choice(source) for _ in range(1000)]
    assert examples[:10] == ['d', 'a', 'c', 'c', 'd', 'd', 'd', 'b', 'c', 'a']
    from collections import Counter
    distribution = Counter(examples)
    assert distribution.most_common() == [('d', 551), ('c', 271), ('b', 126), ('a', 52)]


### Lexicon.

# For this application, weighted choices are strings.

WeightedChoices = List[Tuple[str, int]]


class WordMaker:
    """Create words from a few rules.

    1. Markov chains based on digraphs.
    2. Initial Letter thrown on kind of randomly.
    3. Seeded RNG from source word.
    """

    # https://www.math.cornell.edu/~mec/2003-2004/cryptography/subs/digraphs.html
    digraph_text = dedent('''\
    Digraph	Count	 	Digraph	Frequency
    th	5532	 	th	1.52
    he	4657	 	he	1.28
    in	3429	 	in	0.94
    er	3420	 	er	0.94
    an	3005	 	an	0.82
    re	2465	 	re	0.68
    nd	2281	 	nd	0.63
    at	2155	 	at	0.59
    on	2086	 	on	0.57
    nt	2058	 	nt	0.56
    ha	2040	 	ha	0.56
    es	2033	 	es	0.56
    st	2009	 	st	0.55
    en	2005	 	en	0.55
    ed	1942	 	ed	0.53
    to	1904	 	to	0.52
    it	1822	 	it	0.50
    ou	1820	 	ou	0.50
    ea	1720	 	ea	0.47
    hi	1690	 	hi	0.46
    is	1660	 	is	0.46
    or	1556	 	or	0.43
    ti	1231	 	ti	0.34
    as	1211	 	as	0.33
    te	985	 	te	0.27
    et	704	 	et	0.19
    ng	668	 	ng	0.18
    of	569	 	of	0.16
    al	341	 	al	0.09
    de	332	 	de	0.09
    se	300	 	se	0.08
    le	298	 	le	0.08
    sa	215	 	sa	0.06
    si	186	 	si	0.05
    ar	157	 	ar	0.04
    ve	148	 	ve	0.04
    ra	137	 	ra	0.04
    ld	64	 	ld	0.02
    ur	60	 	ur	0.02
    ''')

    # https://en.wikipedia.org/wiki/Letter_frequency
    first_letter_text = dedent('''\
    Letter	Frequency
    z	0.034%
    y	1.620%
    x	0.017%
    w	6.753%
    v	0.649%
    u	1.487%
    t	16.671%
    s	7.755%
    r	1.653%
    q	0.173%
    p	2.545%
    o	6.264%
    n	2.365%
    m	4.383%
    l	2.705%
    k	0.590%
    j	0.597%
    i	6.286%
    h	7.232%
    g	1.950%
    f	3.779%
    e	2.007%
    d	2.670%
    c	3.511%
    b	4.702%
    a	11.602%
    ''')

    # Real data: http://norvig.com/mayzner.html
    # Handy approximation
    # word lengths are 2 to 12, linear 200 down to 20 occurrences.
    # (x, y) = (2, 200)
    # (x, y) = (12, 20)
    # m = Fraction(200-20)/Fraction(2-12) = -18
    # b = 200-m*2 = 236
    lengths = [(x, 236-18*x) for x in range(2,13)]

    def __init__(self, make_seed: Callable[[str], int]) -> None:
        """
        Prepare the generator using a seed-creating function
        and loading the frequency tables.

        :param make_seed: a function to transform English word to a seed for generating a ConLang word.
        """
        self.load_digraph_markov()
        self.load_first_letters()
        self.make_seed = make_seed

    def load_digraph_markov(self) -> None:
        source_file = io.StringIO(self.digraph_text)
        reader = csv.DictReader(source_file, delimiter='\t', skipinitialspace=True)
        self.digraphs: WeightedChoices = list(
            (row['Digraph'], int(row['Count']))
            for row in reader
        )

        # The digraphs -- alone -- aren't very English like.
        # Turning them into Markov Chains is more useful.

        self.markov: Dict[str, WeightedChoices] = defaultdict(list)
        for digraph, count in self.digraphs:
            start, nextc = digraph
            self.markov[start].append((nextc, count))

    def load_first_letters(self) -> None:
        source_file = io.StringIO(self.first_letter_text)
        reader = csv.DictReader(source_file, delimiter='\t', skipinitialspace=True)
        self.first_letters = list((row['Letter'], 1000*float(row['Frequency'][:-1])) for row in reader)

    def word(self, seed: str = "") -> str:
        """Expand weighted Markov chains through the digraphs."""
        if seed:
            random.seed(self.make_seed(seed))

        target_length = weighted_choice(self.lengths)
        c_1, c_2 = weighted_choice(self.digraphs)
        if target_length == 2:
            w = [c_1, c_2]
        else:
            c_0 = weighted_choice(self.first_letters)
            w = [c_0, c_1, c_2]

        while len(w) < target_length:
            if w[-1] in self.markov:
                w.append(weighted_choice(self.markov[w[-1]]))
            else:
                target_length += 2
                c_1, c_2 = weighted_choice(self.digraphs)
                w.extend(["'", c_1, c_2])
        return ''.join(w)


def naive_seed(original: str) -> int:
    """Transform source word into RNG seed. Seems to have too many collisions."""
    return sum(original.encode('ascii'))


def hash_seed(original: str) -> int:
    """Transform source word into RNG seed."""
    return sum(hashlib.sha1(original.encode('ascii')).digest())


def test_wordmaker() -> None:
    m = WordMaker(lambda n: n)
    words = [m.word(n) for n in range(1, 100, 10)]
    assert words == ['is', 'aesth', 'to', 'he', 'tere', 'tnt', 'cesth', 'yeng', 'jonde', 'in']
    random.seed(42)
    lexicon = [m.word() for _ in range(5000)]
    from collections import Counter
    first = Counter(w[0] for w in lexicon)
    pct = sorted(((letter, 100*count/5000) for letter, count in first.most_common()), reverse=True)
    assert pct[:5] == [('z', 0.02), ('y', 1.2), ('x', 0.02), ('w', 4.62), ('v', 0.74)]
    assert pct[-5:] == [('e', 4.7), ('d', 2.4), ('c', 3.38), ('b', 4.22), ('a', 11.22)]


### Grammar.

# We don't parse English into the tagged structure.
# The material to be translated needs to be marked up manually.
# (Use NLTK to create tagged structures https://www.nltk.org/api/nltk.parse.stanford.html)


class Tag(NamedTuple):
    """Tagged text that forms a tree. (Similar to NLTK.Tree.)"""
    pos: str  # Part of Speech. "S", "NP", "VP", "ADVP", "MD", "TV", "IV", "DatV", "SV", "PP", "IN"
    words: list['str | Tag']  # Terminal or Tag

    @staticmethod
    def from_text(source: str) -> "Tag":
        """Parse (tag (tag word) (tag word)) kinds of structures."""
        lex_pat = re.compile(r"\(|\)|\s+|[^\s()]+")
        tokens = (t for t in lex_pat.findall(source) if not t.isspace())
        symbols = deque(tokens)
        return Tag.from_symbols(symbols)

    @staticmethod
    def from_symbols(symbols: List[str]) -> "Tag":
        assert symbols.popleft() == "(", f'Invalid structure {symbols}'
        tag = symbols.popleft()
        words = []
        while symbols[0] != ")":
            if symbols[0] == "(":
                words.append(Tag.from_symbols(symbols))
            else:
                words.append(symbols.popleft())
        assert symbols.popleft() == ")", f'Invalid structure {symbols}'
        return Tag(tag, words)

    def __str__(self) -> str:
        text = []
        for w in self.words:
            if isinstance(w, str):
                text.append(w)
            else:
                text.append(str(w))
        return f"({self.pos} {' '.join(text)})"

    def __repr__(self) -> str:
        return f"Tag({self.pos!r}, [{', '.join(repr(c) for c in self.words)}])"

    def clean(self) -> str:
        text = []
        for w in self.words:
            if isinstance(w, str):
                text.append(w)
            else:
                text.append(w.clean())
        return " ".join(text)


def test_tag() -> None:
    src = '(S (VP (TV kill) (NP (DET the) (NP mage))))'
    t = Tag.from_text(src)
    assert t == Tag(pos='S', words=[
            Tag(pos='VP', words=[
                Tag(pos='TV', words=['kill']),
                Tag(pos='NP', words=[
                    Tag(pos='DET', words=['the']),
                    Tag(pos='NP', words=['mage'])
                ])
            ])
        ])
    assert str(t) == "(S (VP (TV kill) (NP (DET the) (NP mage))))"
    assert t.clean() == "kill the mage"


class TransformRule:
    """Find a structure like (TAG $x $y) and transform to (TAG $y $x).

    This has a number of limitations, of course.
    Principally, it doesn't use Chomsky Normal Form.
    In CNF, every production having either two non-terminals or one terminal on the right-hand side.
    This seems similar to the way lambda calculus rewrites higher-arity operators as single-operand lambdas.

    ..  todo:: Expand placeholders to include transformations like stemming a word.
    """
    def __init__(self, source: str, target: str):
        self.tag_source = Tag.from_text(source)
        self.tag_target = Tag.from_text(target)

    def match(self, tag_source: Tag, some_content: Tag) -> bool:
        """Match the entire tag pattern and the content being examined."""
        if some_content.pos == tag_source.pos:
            # Descend to see if internal structure inside *also* matches
            child_matches = []
            for src_child, content_child in itertools.zip_longest(tag_source.words, some_content.words):
                if not src_child or not content_child:
                    # lengths do not match
                    child_matches.append(False)
                elif isinstance(src_child, str):
                    # Two kinds of strings, placeholders and terminals.
                    if src_child.startswith("$"):
                        # Placeholder, e.g. "$x", matches anything.
                        child_matches.append(True)
                    else:
                        # Terminals must match
                        child_matches.append(src_child.lower() == content_child.lower())
                elif isinstance(src_child, Tag):
                    # Tag, e.g. ("PP", [words])
                    child_matches.append(self.match(src_child, content_child))
                else:
                    raise ValueError(f"{src_child} in {tag_source.words}")

            return all(child_matches)
        return False

    def placeholders(self, tag_source: Tag, some_content: Tag, variables: Dict[str, Union[Tag, str]]) -> None:
        """
        Given a pattern and tagged content, locate and assign values to $ placeholders.
        This does a recursive depth-first search.

        ..  todo:: Tolerate ``${w|stem}`` which will apply a ``stem()`` function to ``w``.
        """
        for src_child, content_child in zip(tag_source.words, some_content.words):
            if isinstance(src_child, str):
                if src_child.startswith("$"):
                    variables[src_child] = content_child
            else: # Tag, e.g. ("PP", [words])
                self.placeholders(src_child, content_child, variables)

    def emit(self, tag_target: Tag, variables: Dict[str, Union[Tag, str]]) -> Tag:
        """Replace ``$`` placeholders with values. Apply functions like ``${x|stem}``"""
        rewrite = Tag(tag_target.pos, [])
        for w in tag_target.words:
            if isinstance(w, str):
                if w.startswith("$"):
                    rewrite.words.append(variables.get(w, Tag("X", ["?"])))
                else: # Literal
                    rewrite.words.append(w)
            else: # Tag
                rewrite.words.append(self.emit(w, variables))
        return rewrite

    def apply(self, some_content: Tag) -> Tag:
        """
        Apply this rule to some tagged content.
        """
        if self.match(self.tag_source, some_content):
            # Return revised content.
            variables: Dict[str, Union[Tag, str]] = {}
            self.placeholders(self.tag_source, some_content, variables)
            return self.emit(self.tag_target, variables)

        # Descend into structure looking for a match.
        # Return a copy of the original with ONLY matching children changed.
        rewrite = Tag(some_content.pos, [])
        for w in some_content.words:
            # RECURSIVE DESCENT -- depth-first.
            if isinstance(w, str):
                # Terminal is untouched
                rewrite.words.append(w)
            elif isinstance(w, Tag):
                # Tag might be rewritten
                rewrite.words.append(self.apply(w))
            else:
                raise ValueError(f"{w} in {some_content}")

        return rewrite

def test_transform_rule():
    rule1 = TransformRule("(S (NP $n) (VP $v $n2))", "(S (VP $v) (NP $n) (PP a $n2))")
    sa = Tag.from_text("(S (NP I) (VP am (NP groot)))")
    xform_sa1 = rule1.apply(sa)
    assert xform_sa1 == Tag(pos='S', words=[
        Tag(pos='VP', words=["am"]),
        Tag(pos='NP', words=["I"]),
        Tag(pos='PP', words=[
            "a",
            Tag(pos='NP', words=["groot"])
        ])
    ])
    assert str(xform_sa1) == "(S (VP am) (NP I) (PP a (NP groot)))"
    assert xform_sa1.clean() == "am I a groot"

def test_rule_pair():
    rule1 = TransformRule("(S (NP (DET $d) (N $n)) (VP $v $n2))", "(S (VP $v) (NP $n $d) $n2)")
    rule2 = TransformRule("(VP $x (ADVP (NP $y)))", "(VP $x (PP with (NP $y)))")
    sb = Tag.from_text("(S (NP (DET the) (N mage)) (VP dies (ADVP (NP slowly))))")
    xform_sb2 = rule2.apply(sb)
    xform_sb1 = rule1.apply(xform_sb2)
    assert str(xform_sb1) == "(S (VP dies) (NP mage the) (PP with (NP slowly)))"
    assert xform_sb1.clean() == "dies mage the with slowly"


# Main App(s)

def translate(source: str, maker: WordMaker) -> tuple[Tag, list[str]]:
    """
    Use the given WordMaker and transformation rules to translate a tagged sentence.

    ..  todo::

        -   R1-a. See test_transform_rule
        -   R1-b. See test_rule_pair, but reformat noun-determiner ``(NP ${n|suffix(d)})``
        -   R1-c. Special case with no determiner, inject generic "a".
        -   R2. Stem the adverb to drop the adverbial suffix "-ly", ``(VP ${v|stem|tense(m)})``
        -   R3. Rewrite individual verbs with mode/tense as suffix. ``(VP (MD $m) (VP $v)) -> (VP ${v|stem|tense(m)})`` add tense prefix to verb
        -   R4. Rewrite individual nouns with determiners ``(NP (DET $d) (N $n)) -> (NP ${n|suffix(d)})``

    """

    # Special case of no-determiner.
    rule1c = TransformRule("(S (NP $n) (VP $v $n2))",
                          "(S (VP $v) (NP $n) (PP a $n2))")
    phrase = Tag.from_text(source)
    xform_s1 = rule1c.apply(phrase)

    words = (maker.word(w) for w in xform_s1.clean().split())
    return xform_s1, list(words)


def get_options(args: List[str] = sys.argv[1:]) -> argparse.Namespace:
    seed_algo = {'h': hash_seed, 'hash': hash_seed,
        'n': naive_seed, 'naive': naive_seed}
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--algorithm', type=str, action='store', default='hash')
    parser.add_argument('-g', '--generate', type=int, action='store', default=None, help="spew words")
    parser.add_argument('-w', '--words', type=int, action='store', default=None, help="translate words")
    parser.add_argument('-t', '--translate', type=str, action='store', default=None, help="translate a tagged phrase")
    options = parser.parse_args(args)
    try:
        options.algorithm = seed_algo[options.algorithm]
    except KeyError as ex:
        msg = "Alogorithm {} isn't known".format(ex)
        raise argparse.ArgumentTypeError(msg)
    return options


def main() -> None:
    options = get_options()
    maker = WordMaker(options.algorithm)

    if options.generate is not None:
        for i in range(options.generate):
            print(maker.word())

    if options.words is not None:
        for w in options.words.split():
            print(w, maker.word(w))

    if options.translate is not None:
        tagged, words = translate(options.translate, maker)
        print(options.translate, tagged.clean(), words )

if __name__ == "__main__":
    main()
