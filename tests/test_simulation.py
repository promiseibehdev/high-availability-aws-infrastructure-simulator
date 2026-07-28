from dataclasses import FrozenInstanceError

import pytest

from src.architecture import build_reference_architecture
from src.models import AlarmState, HealthState, InstanceLifecycle, ResourceStatus
from src.simulation import EventType, SimulationEngine


def event_types(result):
    return [item.event_type for item in result.events]


def snapshot_after(result, event_type):
    event_index = event_types(result).index(event_type)
    return result.snapshots[event_index + 1]


def test_normal_operation_balances_requests_across_two_healthy_instances():
    result = SimulationEngine().run_normal_operation()

    assert result.scenario_name == "normal_operation"
    assert event_types(result) == [EventType.NORMAL_OPERATION]
    assert result.events[0].timestamp == 0
    assert result.final_snapshot.request_rate == 100
    assert len(result.final_snapshot.instances) == 2
    assert {item.request_count for item in result.final_snapshot.instances} == {50}
    assert all(item.health is HealthState.HEALTHY for item in result.final_snapshot.instances)
    assert result.final_snapshot.load_balancer_status is ResourceStatus.HEALTHY


def test_every_event_has_required_audit_fields_and_ordered_timestamps():
    result = SimulationEngine().run_availability_zone_outage()

    assert all(isinstance(item.timestamp, int) for item in result.events)
    assert all(item.affected_resource.strip() for item in result.events)
    assert all(item.explanation.strip() for item in result.events)
    assert [item.timestamp for item in result.events] == sorted(
        item.timestamp for item in result.events
    )


def test_instance_failure_follows_health_check_and_replacement_sequence():
    result = SimulationEngine().run_instance_failure()

    assert event_types(result) == [
        EventType.NORMAL_OPERATION,
        EventType.INSTANCE_FAILED,
        EventType.HEALTH_CHECK_FAILED,
        EventType.TARGET_DEREGISTERED,
        EventType.REPLACEMENT_LAUNCHED,
        EventType.TARGET_REGISTERED,
        EventType.RECOVERY_COMPLETED,
    ]


def test_failed_target_is_removed_before_replacement_is_registered():
    result = SimulationEngine().run_instance_failure()
    deregistered = snapshot_after(result, EventType.TARGET_DEREGISTERED)
    registered = snapshot_after(result, EventType.TARGET_REGISTERED)

    assert "i-app-a" not in deregistered.registered_target_ids
    assert len(deregistered.registered_target_ids) == 1
    assert "i-failure-001" in registered.registered_target_ids
    assert len(registered.registered_target_ids) == 2


def test_instance_failure_finishes_with_healthy_multi_az_capacity():
    engine = SimulationEngine()
    result = engine.run_instance_failure()

    assert result.final_snapshot.desired_capacity == 2
    assert len(result.final_snapshot.instances) == 2
    assert {item.availability_zone for item in result.final_snapshot.instances} == {
        "us-east-1a",
        "us-east-1b",
    }
    assert all(item.health is HealthState.HEALTHY for item in result.final_snapshot.instances)
    assert result.final_snapshot.load_balancer_status is ResourceStatus.HEALTHY
    assert all(item.state is AlarmState.OK for item in result.final_snapshot.alarms)


def test_health_check_failure_activates_unhealthy_target_alarm():
    result = SimulationEngine().run_instance_failure()
    health_check_snapshot = snapshot_after(result, EventType.HEALTH_CHECK_FAILED)
    alarm_states = {
        item.resource_id: item.state for item in health_check_snapshot.alarms
    }

    assert alarm_states["alarm-unhealthy-hosts"] is AlarmState.ALARM


def test_traffic_spike_triggers_alarm_scale_out_and_scale_in():
    result = SimulationEngine().run_traffic_spike()

    assert event_types(result) == [
        EventType.NORMAL_OPERATION,
        EventType.TRAFFIC_SPIKE,
        EventType.ALARM_TRIGGERED,
        EventType.SCALE_OUT,
        EventType.TRAFFIC_NORMALIZED,
        EventType.SCALE_IN,
    ]
    scale_out = snapshot_after(result, EventType.SCALE_OUT)
    assert scale_out.desired_capacity == 4
    assert len(scale_out.instances) == 4
    assert len(scale_out.registered_target_ids) == 4
    assert {item.availability_zone for item in scale_out.instances} == {
        "us-east-1a",
        "us-east-1b",
    }


def test_traffic_normalization_clears_alarm_before_scale_in():
    result = SimulationEngine().run_traffic_spike()
    spike = snapshot_after(result, EventType.ALARM_TRIGGERED)
    normalized = snapshot_after(result, EventType.TRAFFIC_NORMALIZED)

    spike_alarms = {item.resource_id: item.state for item in spike.alarms}
    normalized_alarms = {item.resource_id: item.state for item in normalized.alarms}
    assert spike_alarms["alarm-high-cpu"] is AlarmState.ALARM
    assert normalized_alarms["alarm-high-cpu"] is AlarmState.OK
    assert normalized.request_rate == 120


def test_scale_in_returns_to_original_capacity():
    engine = SimulationEngine()
    result = engine.run_traffic_spike()

    assert result.final_snapshot.desired_capacity == 2
    assert len(result.final_snapshot.instances) == 2
    assert set(result.final_snapshot.registered_target_ids) == {"i-app-a", "i-app-b"}
    assert engine.state.auto_scaling_group.maximum_capacity == 4


def test_availability_zone_outage_marks_zone_and_resources_unavailable():
    engine = SimulationEngine()
    result = engine.run_availability_zone_outage()
    outage = snapshot_after(result, EventType.AVAILABILITY_ZONE_OUTAGE)

    assert outage.unavailable_zones == frozenset({"us-east-1a"})
    assert outage.load_balancer_status is ResourceStatus.DEGRADED
    assert any(
        item.availability_zone == "us-east-1a" and item.health is HealthState.UNHEALTHY
        for item in outage.instances
    )


def test_zone_outage_reroutes_and_restores_capacity_in_healthy_zone():
    result = SimulationEngine().run_availability_zone_outage()
    rerouted = snapshot_after(result, EventType.TRAFFIC_REROUTED)
    replacement = snapshot_after(result, EventType.REPLACEMENT_LAUNCHED)

    assert len(rerouted.registered_target_ids) == 1
    assert len(replacement.registered_target_ids) == 2
    assert all(
        item.availability_zone == "us-east-1b" for item in replacement.instances
    )


def test_zone_recovery_rebalances_instances_across_both_zones():
    engine = SimulationEngine()
    result = engine.run_availability_zone_outage()

    assert EventType.RECOVERY_STARTED in event_types(result)
    assert EventType.CAPACITY_REBALANCED in event_types(result)
    assert EventType.RECOVERY_COMPLETED in event_types(result)
    assert result.final_snapshot.unavailable_zones == frozenset()
    assert {item.availability_zone for item in result.final_snapshot.instances} == {
        "us-east-1a",
        "us-east-1b",
    }
    assert result.final_snapshot.load_balancer_status is ResourceStatus.HEALTHY
    assert result.final_snapshot.target_group_status is ResourceStatus.HEALTHY
    assert all(
        item.lifecycle is InstanceLifecycle.IN_SERVICE
        for item in result.final_snapshot.instances
    )


def test_snapshots_are_immutable():
    result = SimulationEngine().run_normal_operation()

    with pytest.raises(FrozenInstanceError):
        result.final_snapshot.request_rate = 999
    with pytest.raises(FrozenInstanceError):
        result.final_snapshot.instances[0].request_count = 999


def test_engine_does_not_mutate_caller_owned_initial_state():
    initial = build_reference_architecture()
    original_instance_ids = [item.resource_id for item in initial.instances]

    SimulationEngine(initial).run_instance_failure()

    assert [item.resource_id for item in initial.instances] == original_instance_ids
    assert initial.instance("i-app-a").health is HealthState.HEALTHY


@pytest.mark.parametrize(
    "runner_name",
    [
        "run_normal_operation",
        "run_instance_failure",
        "run_traffic_spike",
        "run_availability_zone_outage",
    ],
)
def test_scenario_runs_are_deterministic(runner_name):
    first = getattr(SimulationEngine(), runner_name)()
    second = getattr(SimulationEngine(), runner_name)()

    assert first == second
