"""A few test cases for the features module."""
from textwrap import dedent
import pytest
from typer.testing import CliRunner

import fictool.features as features
import fictool.main as main

@pytest.fixture
def cli_runner():
    runner = CliRunner()
    return runner

def test_features(capfd):
    features.describe("author")
    out, err = capfd.readouterr()
    assert out.splitlines() == ['author', 'Hair Curl: Injured', 'Hair Coverage: Small', 'Ears: Large', 'Eyebrows: Small', 'Eyes: Missing', 'Teeth: Small', 'Chin: Small', 'Shoulders: Large', 'Arms: Injured', 'Chest: Injured', 'Gut: Small', 'Hips: Large', 'Knees: Small', 'Overall Size: Small', '']

def test_app_features(cli_runner):
    result = cli_runner.invoke(main.app, ["features", "author"])
    assert result.exit_code == 0
    assert result.output == dedent("""\
                  author           
        ┏━━━━━━━━━━━━━━━┳━━━━━━━━━┓
        ┃ Attribute     ┃ Value   ┃
        ┡━━━━━━━━━━━━━━━╇━━━━━━━━━┩
        │ Hair Curl     │ Injured │
        │ Hair Coverage │ Small   │
        │ Ears          │ Large   │
        │ Eyebrows      │ Small   │
        │ Eyes          │ Missing │
        │ Teeth         │ Small   │
        │ Chin          │ Small   │
        │ Shoulders     │ Large   │
        │ Arms          │ Injured │
        │ Chest         │ Injured │
        │ Gut           │ Small   │
        │ Hips          │ Large   │
        │ Knees         │ Small   │
        │ Overall Size  │ Small   │
        └───────────────┴─────────┘
        
        """)
