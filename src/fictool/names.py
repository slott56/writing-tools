"""
Common English Nouns

http://www.talkenglish.com/vocabulary/top-1500-nouns.aspx
"""

import random
import re

from typing import Iterator

from data.words import words


def corpus_iter() -> Iterator[str]:
    word_pat = re.compile(r"(\w+)\s+(\d+)\s+\(([\w,]+)\)")
    lines = filter(None, words.splitlines())
    matches = filter(None, (word_pat.match(line) for line in lines))
    for m in matches:
        # print(m.groups())
        # print(m.group(1), m.group(3).split(','))
        yield m.group(1)


def generate_names(n: int) -> list[str]:
    corpus = list(corpus_iter())

    names = random.sample(corpus, n)

    return names
