"""Deterministic CloudWatch-style monitoring projections for simulator snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from src.models import AlarmState, ResourceStatus
from src.simulation import SimulationResult, SimulationSnapshot


@dataclass(frozen=True)
class MetricPoint:
    timestamp: int
    cpu_utilization_percent: float
    request_rate: int
    healthy_host_count: int
    response_time_ms: float


@dataclass(frozen=True)
class AlarmTransition:
    timestamp: int
    alarm_id: str
    previous_state: AlarmState
    current_state: AlarmState
    explanation: str


@dataclass(frozen=True)
class MonitoringView:
    current: MetricPoint
    history: tuple[MetricPoint, ...]
    active_alarm_ids: tuple[str, ...]
    alarm_history: tuple[AlarmTransition, ...]
    recovery_status: str


def build_monitoring_view(result: SimulationResult, step: int) -> MonitoringView:
    """Build monitoring data through one selected timeline step."""

    selected_step = max(0, min(step, len(result.events)))
    snapshots = result.snapshots[: selected_step + 1]
    history = tuple(_metric_point(snapshot) for snapshot in snapshots)
    current_snapshot = snapshots[-1]
    active_alarm_ids = tuple(
        item.resource_id
        for item in current_snapshot.alarms
        if item.state is AlarmState.ALARM
    )
    return MonitoringView(
        current=history[-1],
        history=history,
        active_alarm_ids=active_alarm_ids,
        alarm_history=_alarm_transitions(snapshots),
        recovery_status=_recovery_status(
            result, selected_step, current_snapshot, active_alarm_ids
        ),
    )


def _metric_point(snapshot: SimulationSnapshot) -> MetricPoint:
    healthy_count = sum(item.health.value == "healthy" for item in snapshot.instances)
    average_cpu = (
        sum(item.cpu_utilization_percent for item in snapshot.instances)
        / len(snapshot.instances)
        if snapshot.instances
        else 0.0
    )
    status_penalty = {
        ResourceStatus.HEALTHY: 0.0,
        ResourceStatus.DEGRADED: 85.0,
        ResourceStatus.UNHEALTHY: 160.0,
        ResourceStatus.UNAVAILABLE: 250.0,
    }[snapshot.load_balancer_status]
    load_penalty = snapshot.request_rate / max(healthy_count * 20, 1)
    response_time = round(30.0 + average_cpu * 0.45 + load_penalty + status_penalty, 1)
    return MetricPoint(
        timestamp=snapshot.timestamp,
        cpu_utilization_percent=round(average_cpu, 1),
        request_rate=snapshot.request_rate,
        healthy_host_count=healthy_count,
        response_time_ms=response_time,
    )


def _alarm_transitions(
    snapshots: tuple[SimulationSnapshot, ...],
) -> tuple[AlarmTransition, ...]:
    transitions: list[AlarmTransition] = []
    for previous, current in pairwise(snapshots):
        previous_states = {item.resource_id: item.state for item in previous.alarms}
        for alarm in current.alarms:
            previous_state = previous_states[alarm.resource_id]
            if alarm.state is previous_state:
                continue
            transitions.append(
                AlarmTransition(
                    timestamp=current.timestamp,
                    alarm_id=alarm.resource_id,
                    previous_state=previous_state,
                    current_state=alarm.state,
                    explanation=(
                        f"{alarm.resource_id} changed from {previous_state.value} "
                        f"to {alarm.state.value}."
                    ),
                )
            )
    return tuple(transitions)


def _recovery_status(
    result: SimulationResult,
    step: int,
    snapshot: SimulationSnapshot,
    active_alarm_ids: tuple[str, ...],
) -> str:
    if snapshot.unavailable_zones:
        return "Failover in progress"
    if active_alarm_ids or snapshot.load_balancer_status is not ResourceStatus.HEALTHY:
        return "Degraded - automated response active"
    if step == len(result.events) and result.scenario_name != "normal_operation":
        return "Recovery complete"
    if step == 0:
        return "Ready for simulation"
    return "Healthy and stable"
