from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import app
from src.architecture import build_reference_architecture
from src.scenarios import ScenarioName, run_scenario
from src.ui import (
    build_architecture_dot,
    build_resource_details,
)


def make_app_test():
    return AppTest.from_file(str(Path(app.__file__)), default_timeout=20)


def rendered_text(app_test):
    values = []
    for collection_name in (
        "title",
        "header",
        "subheader",
        "markdown",
        "caption",
        "info",
        "warning",
        "error",
        "success",
    ):
        collection = getattr(app_test, collection_name, [])
        values.extend(str(item.value) for item in collection)
    return "\n".join(values)


def open_simulator():
    app_test = make_app_test()
    app_test.run()
    app_test.button(key="open_simulator").click().run()
    return app_test


def test_landing_page_is_recruiter_friendly_and_explicitly_simulated():
    app_test = make_app_test()
    app_test.run()
    text = rendered_text(app_test)

    assert not app_test.exception
    assert "High-Availability AWS Infrastructure Simulator" in text
    assert "100% OFFLINE SIMULATION" in text
    assert "Simulation-only environment" in text
    assert "No metrics on this page come from AWS" in text
    assert app_test.button(key="start_guided_tour")
    assert app_test.button(key="open_simulator")


def test_open_simulator_renders_complete_dashboard_without_external_setup():
    app_test = open_simulator()
    text = rendered_text(app_test)

    assert not app_test.exception
    for heading in (
        "Scenario controls",
        "Infrastructure status",
        "CloudWatch-style alarms",
        "Interactive architecture",
        "Simulated metrics",
        "Resource explorer",
        "Event timeline",
    ):
        assert heading in text
    assert app_test.button(key="reset_simulation")
    assert app_test.button(key="next_event")


def test_guided_tour_opens_instance_failure_walkthrough():
    app_test = make_app_test()
    app_test.run()
    app_test.button(key="start_guided_tour").click().run()

    assert not app_test.exception
    assert "Guided Tour" in rendered_text(app_test)
    assert app_test.session_state["active_scenario"] == "instance_failure"
    assert app_test.session_state["timeline_step"] == 0


def test_next_event_reveals_one_timeline_step_at_a_time():
    app_test = make_app_test()
    app_test.run()
    app_test.button(key="start_guided_tour").click().run()
    app_test.button(key="next_event").click().run()
    text = rendered_text(app_test)

    assert not app_test.exception
    assert app_test.session_state["timeline_step"] == 1
    assert "NORMAL OPERATION" in text
    assert "The ALB distributes traffic" in text


def test_scenario_selector_connects_to_existing_engine():
    app_test = open_simulator()
    app_test.selectbox(key="scenario_selector").select("traffic_spike")
    app_test.button(key="run_selected_scenario").click().run()

    assert not app_test.exception
    assert app_test.session_state["active_scenario"] == "traffic_spike"
    assert app_test.session_state["simulation_result"].scenario_name == "traffic_spike"
    assert app_test.session_state["timeline_step"] == 0


def test_reset_returns_current_scenario_to_initial_snapshot():
    app_test = make_app_test()
    app_test.run()
    app_test.button(key="start_guided_tour").click().run()
    app_test.button(key="next_event").click().run()
    app_test.button(key="next_event").click().run()
    assert app_test.session_state["timeline_step"] == 2

    app_test.button(key="reset_simulation").click().run()

    assert not app_test.exception
    assert app_test.session_state["timeline_step"] == 0


def test_previous_control_replays_the_prior_immutable_snapshot():
    app_test = make_app_test()
    app_test.run()
    app_test.button(key="start_guided_tour").click().run()
    app_test.button(key="next_event").click().run()
    app_test.button(key="next_event").click().run()
    result = app_test.session_state["simulation_result"]

    app_test.button(key="previous_event").click().run()

    assert not app_test.exception
    assert app_test.session_state["timeline_step"] == 1
    assert app_test.session_state["simulation_result"] == result


@pytest.mark.parametrize("scenario", list(ScenarioName))
def test_ui_runs_every_supported_scenario(scenario):
    app_test = open_simulator()
    app_test.selectbox(key="scenario_selector").select(scenario.value)
    app_test.button(key="run_selected_scenario").click().run()

    assert not app_test.exception
    assert app_test.session_state["active_scenario"] == scenario.value
    assert app_test.session_state["simulation_result"].scenario_name == scenario.value


def test_invalid_session_result_recovers_to_safe_normal_scenario():
    app_test = open_simulator()
    app_test.session_state["simulation_result"] = "invalid"
    app_test.session_state["active_scenario"] = "not-a-scenario"

    app_test.run()

    assert not app_test.exception
    assert app_test.session_state["active_scenario"] == "normal_operation"
    assert app_test.session_state["simulation_result"].scenario_name == "normal_operation"


def test_resource_details_cover_every_modeled_and_dynamic_resource():
    architecture = build_reference_architecture()
    snapshot = run_scenario(ScenarioName.TRAFFIC_SPIKE).snapshots[3]
    details = build_resource_details(architecture, snapshot)
    resource_ids = {item.resource_id for item in details}

    expected_static_ids = {
        architecture.vpc.resource_id,
        architecture.internet_gateway.resource_id,
        architecture.load_balancer.resource_id,
        architecture.target_group.resource_id,
        architecture.auto_scaling_group.resource_id,
        architecture.iam_role.resource_id,
        architecture.s3_bucket.resource_id,
        *(item.resource_id for item in architecture.subnets),
        *(item.resource_id for item in architecture.route_tables),
        *(item.resource_id for item in architecture.security_groups),
        *(item.resource_id for item in architecture.cloudwatch.alarms),
    }
    assert expected_static_ids.issubset(resource_ids)
    assert {item.resource_id for item in snapshot.instances}.issubset(resource_ids)
    assert all(item.description and item.attributes for item in details)


def test_graphviz_dot_reflects_dynamic_snapshot_state():
    architecture = build_reference_architecture()
    result = run_scenario(ScenarioName.AVAILABILITY_ZONE_OUTAGE)
    outage = next(
        snapshot
        for snapshot in result.snapshots
        if snapshot.unavailable_zones == frozenset({"us-east-1a"})
    )
    dot = build_architecture_dot(architecture, outage)

    assert dot.startswith("digraph architecture")
    assert "cluster_us-east-1a" in dot
    assert "unavailable" in dot
    assert "Application Load Balancer" in dot
    assert "Target Group" in dot
    assert "/health" in dot


def test_phase_six_adds_terraform_explorer():
    app_test = open_simulator()
    text = rendered_text(app_test)

    for heading in (
        "Monitoring dashboard",
        "Security review",
        "Cost awareness",
        "Educational mode",
        "Terraform Explorer",
        "Terraform lifecycle",
        "Production architecture vs educational simulator",
        "Validation and security checks",
    ):
        assert heading in text
    assert "No AWS Pricing API is used" in text
    assert "Terraform is never executed" in text
    assert any(
        metric.label == "This simulator's AWS cost" and metric.value == "$0.00"
        for metric in app_test.metric
    )


def test_resource_selection_automatically_maps_to_terraform_component():
    app_test = open_simulator()
    app_test.selectbox(key="selected_resource").select("s3-artifacts").run()

    assert not app_test.exception
    assert app_test.selectbox(key="terraform_component").value == "s3"
    assert "S3 Bucket" in rendered_text(app_test)


def test_ui_runtime_contains_no_aws_or_network_clients():
    project_root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        (project_root / path).read_text(encoding="utf-8").lower()
        for path in ("app.py", "src/ui.py")
    )
    forbidden = (
        "import boto3",
        "import requests",
        "import socket",
        "aws_access_key",
        "http://",
        "https://",
    )

    assert all(term not in source for term in forbidden)


def test_theme_includes_mobile_reflow_and_keyboard_focus_visibility():
    source = (Path(__file__).resolve().parents[1] / "src/ui.py").read_text(
        encoding="utf-8"
    )

    assert "@media (max-width: 760px)" in source
    assert "flex: 1 1 100%" in source
    assert ":focus-visible" in source
    assert "outline: 3px solid #2563eb" in source
