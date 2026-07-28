"""Named, replayable scenario catalog for the offline simulator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from src.simulation import SimulationEngine, SimulationResult


class ScenarioName(str, Enum):
    NORMAL_OPERATION = "normal_operation"
    INSTANCE_FAILURE = "instance_failure"
    TRAFFIC_SPIKE = "traffic_spike"
    AVAILABILITY_ZONE_OUTAGE = "availability_zone_outage"


@dataclass(frozen=True)
class ScenarioDefinition:
    name: ScenarioName
    title: str
    summary: str
    runner: Callable[[SimulationEngine], SimulationResult]


SCENARIOS = {
    ScenarioName.NORMAL_OPERATION: ScenarioDefinition(
        name=ScenarioName.NORMAL_OPERATION,
        title="Normal operation",
        summary="Traffic is balanced across healthy instances in two Availability Zones.",
        runner=SimulationEngine.run_normal_operation,
    ),
    ScenarioName.INSTANCE_FAILURE: ScenarioDefinition(
        name=ScenarioName.INSTANCE_FAILURE,
        title="EC2 instance failure",
        summary="Health checks remove a failed target and Auto Scaling replaces it.",
        runner=SimulationEngine.run_instance_failure,
    ),
    ScenarioName.TRAFFIC_SPIKE: ScenarioDefinition(
        name=ScenarioName.TRAFFIC_SPIKE,
        title="Traffic spike and scaling",
        summary="High load triggers scale out before capacity returns to normal.",
        runner=SimulationEngine.run_traffic_spike,
    ),
    ScenarioName.AVAILABILITY_ZONE_OUTAGE: ScenarioDefinition(
        name=ScenarioName.AVAILABILITY_ZONE_OUTAGE,
        title="Availability Zone outage",
        summary="Traffic fails over, replacement capacity starts, and both zones recover.",
        runner=SimulationEngine.run_availability_zone_outage,
    ),
}


def available_scenarios() -> tuple[ScenarioDefinition, ...]:
    """Return scenarios in the stable order used by the interface."""

    return tuple(SCENARIOS[item] for item in ScenarioName)


def run_scenario(name: ScenarioName | str) -> SimulationResult:
    """Run a named scenario from a fresh reference state every time."""

    try:
        scenario_name = name if isinstance(name, ScenarioName) else ScenarioName(name)
    except ValueError as exc:
        valid = ", ".join(item.value for item in ScenarioName)
        raise ValueError(f"Unknown scenario '{name}'. Available scenarios: {valid}.") from exc
    definition = SCENARIOS[scenario_name]
    return definition.runner(SimulationEngine())
