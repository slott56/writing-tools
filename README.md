# Writing tools for TTRPG or Literature

These are not polished, finished, stand-alone applications.
These are frameworks you can customize for the fiction you're working on.

You probably do **not** want to simply run these without further customization.
They're seeds for thought.

1.  ``plot.py`` Uses Tarot card layouts to create a story line.

2.  ``terrain-tk.py``, and ``notebooks/terrain.ipynb`` Draws a hex-grid map. 

3.  ``features.py`` Creates physical features and descriptions of characters.

4.  ``language.py`` Implements a specific conLang for a series of books.
    This includes a few grammar rules and lexicon rules to create words.

5.  ``names.py`` Uses a list of common English nouns;
    this can lead to occupation names (think "smith" and "miller").

6.  ``miseries.py`` Develops human miseries.

7.  ``dice.py`` a DSL for "dice expressions".

A test suite is available. 
To make life simpler, install **uv** (https://docs.astral.sh/uv/getting-started/installation/).
With ``uv`` the various version virtual environments will be built automatically.

..  code-block:: bash

    % uv tool run tox run
