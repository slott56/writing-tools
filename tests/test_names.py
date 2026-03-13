"""A few test cases for the names module."""

import random

import pytest
from typer.testing import CliRunner

import fictool.names  as names
import fictool.main as main

@pytest.fixture
def fixed_seed():
    random.seed(42)

@pytest.fixture
def cli_runner(fixed_seed):
    runner = CliRunner()
    return runner

def test_names(fixed_seed):
    n = names.generate_names(2)
    assert n == ['meet', 'storage']

def test_app_names(cli_runner):
    result = cli_runner.invoke(main.app, ["words", "2"])
    assert result.exit_code == 0
    assert result.output == "meet\nstorage\n"
