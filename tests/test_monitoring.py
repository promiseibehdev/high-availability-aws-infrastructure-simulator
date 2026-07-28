from src.monitoring import build_monitoring_view
from src.scenarios import ScenarioName, run_scenario


def test_monitoring_view_matches_initial_snapshot_metrics():
    result = run_scenario(ScenarioName.NORMAL_OPERATION)
    view = build_monitoring_view(result, 0)

    assert len(view.history) == 1
    assert view.current.request_rate == result.snapshots[0].request_rate
    assert view.current.healthy_host_count == 2
    assert view.current.cpu_utilization_percent >= 0
    assert view.current.response_time_ms > 0
    assert view.recovery_status == "Ready for simulation"


def test_traffic_spike_increases_observed_load_and_response_time():
    result = run_scenario(ScenarioName.TRAFFIC_SPIKE)
    initial = build_monitoring_view(result, 0)
    peak = max(
        (build_monitoring_view(result, step) for step in range(len(result.events) + 1)),
        key=lambda view: view.current.request_rate,
    )

    assert peak.current.request_rate > initial.current.request_rate
    assert peak.current.cpu_utilization_percent > initial.current.cpu_utilization_percent
    assert peak.current.response_time_ms > initial.current.response_time_ms


def test_alarm_history_records_deterministic_state_transitions():
    result = run_scenario(ScenarioName.TRAFFIC_SPIKE)
    first = build_monitoring_view(result, len(result.events))
    replay = build_monitoring_view(
        run_scenario(ScenarioName.TRAFFIC_SPIKE), len(result.events)
    )

    assert first == replay
    assert first.alarm_history
    assert all(item.explanation for item in first.alarm_history)


def test_recovered_scenario_reports_recovery_complete():
    result = run_scenario(ScenarioName.INSTANCE_FAILURE)
    view = build_monitoring_view(result, len(result.events))

    assert view.recovery_status == "Recovery complete"
    assert not view.active_alarm_ids
