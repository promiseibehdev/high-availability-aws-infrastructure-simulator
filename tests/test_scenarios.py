from pathlib import Path

import pytest

from src.scenarios import (
    SCENARIOS,
    ScenarioDefinition,
    ScenarioName,
    available_scenarios,
    run_scenario,
)
from src.simulation import EventType, SimulationResult


def test_catalog_exposes_all_supported_scenarios_in_stable_order():
    definitions = available_scenarios()

    assert all(isinstance(item, ScenarioDefinition) for item in definitions)
    assert [item.name for item in definitions] == list(ScenarioName)
    assert set(SCENARIOS) == set(ScenarioName)


@pytest.mark.parametrize("scenario_name", list(ScenarioName))
def test_catalog_runs_every_scenario_from_a_fresh_state(scenario_name):
    result = run_scenario(scenario_name)

    assert isinstance(result, SimulationResult)
    assert result.scenario_name == scenario_name.value
    assert result.events[0].event_type is EventType.NORMAL_OPERATION
    assert len(result.snapshots) == len(result.events) + 1


def test_string_scenario_name_is_supported():
    result = run_scenario("traffic_spike")

    assert EventType.SCALE_OUT in [item.event_type for item in result.events]
    assert EventType.SCALE_IN in [item.event_type for item in result.events]


def test_unknown_scenario_has_an_actionable_error():
    with pytest.raises(ValueError, match="Available scenarios"):
        run_scenario("real_aws_outage")


def test_replaying_catalog_scenario_returns_identical_result():
    first = run_scenario(ScenarioName.AVAILABILITY_ZONE_OUTAGE)
    second = run_scenario(ScenarioName.AVAILABILITY_ZONE_OUTAGE)

    assert first == second
    assert first is not second


def test_phase_three_runtime_has_no_external_service_imports_or_process_calls():
    project_root = Path(__file__).resolve().parents[1]
    runtime_source = "\n".join(
        (project_root / "src" / filename).read_text(encoding="utf-8")
        for filename in ("simulation.py", "scenarios.py")
    ).lower()

    forbidden_terms = (
        "import boto3",
        "import requests",
        "import socket",
        "import subprocess",
        "terraform apply",
        "aws_access_key",
        "http://",
        "https://",
    )
    assert all(term not in runtime_source for term in forbidden_terms)
