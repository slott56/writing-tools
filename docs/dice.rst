###########
  dice.py
###########

A Pythonic definition of a DSL for dice expressions.

::

    3 * D6 + 2

This creates an object with methods for rolling the specified dice,
or computing the min, max, mean, and standard deviation.

Implementation
==============

..  automodule:: dice

Die
----

..  autoclass:: dice.Die
    :members:

Wild Die
--------

..  autoclass:: dice.WildDie
    :members:

UniformValue
-------------

..  autoclass:: dice.UniformValue
    :members:

Interaction
-----------

..  autoclass:: dice.Interaction
    :members:

CLI
----

..  autofunction:: dice.interactive

..  autofunction:: dice.expected

..  autofunction:: dice.roll

..  autofunction:: dice.set_seed



