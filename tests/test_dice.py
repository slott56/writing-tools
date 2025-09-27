"""A few test cases for the dice module."""

import random

import pytest
from typer.testing import CliRunner

import dice

@pytest.fixture
def fixed_seed():
    random.seed(42)

def test_die_minimal(fixed_seed):
    d = 3 * dice.D6 + 2
    assert [d.roll() for _ in range(5)] == [10, 13, 12, 15, 13]
    assert d.min == 5
    assert d.max == 20
    assert d.mean == 12.5
    assert d.stdev == pytest.approx(2.958, abs=1.0E-4)

def test_uniform_minimal(fixed_seed):
    d = dice.UniformValue(0, 99)
    assert [d.roll() for _ in range(5)] == [81, 14, 3, 94, 35]
    assert d.min == 0
    assert d.max == 99
    assert d.mean == 49.5
    assert d.stdev == pytest.approx(7.1763, abs=1.0E-4)

def test_interactive(capsys, fixed_seed):
    cmd = dice.Interaction()
    cmd.namespace = {"D6": dice.D6}
    cmd.preloop()
    cmd.onecmd("3 * D6 + 2")
    out, err = capsys.readouterr()
    assert out == "10\n"
    cmd.onecmd("count 5")
    out, err = capsys.readouterr()
    assert out == "13\n12\n15\n13\n8\n"

@pytest.fixture
def cli_runner(fixed_seed):
    runner = CliRunner()
    return runner

def test_app_expr(cli_runner):
    result = cli_runner.invoke(dice.dice_app, ["3 * D6 + 2"])
    assert result.exit_code == 0
    assert result.output == "10\n"

def test_app_expr_count(cli_runner):
    result = cli_runner.invoke(dice.dice_app, ["3 * D6 + 2", "--count", 5])
    assert result.exit_code == 0
    assert result.output == "10\n13\n12\n15\n13\n"

def test_cli():
    pass
