"""Polished Streamlit presentation layer for the offline simulation engine."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

import streamlit as st

from src.architecture import build_reference_architecture
from src.cost_data import (
    ESTIMATE_DATE,
    ESTIMATE_DISCLAIMER,
    ESTIMATE_REGION,
    PRODUCTION_COST_ESTIMATES,
    estimated_monthly_total,
)
from src.education import COMPONENT_GUIDES, MISCONFIGURATIONS, SECURITY_CONTROLS
from src.models import AlarmState, ArchitectureState, SubnetType
from src.monitoring import build_monitoring_view
from src.scenarios import SCENARIOS, ScenarioName, available_scenarios, run_scenario
from src.simulation import SimulationResult, SimulationSnapshot
from src.terraform_explorer import (
    PRODUCTION_DEMO_COMPARISON,
    TERRAFORM_EXAMPLE_BY_ID,
    TERRAFORM_EXAMPLES,
    TERRAFORM_LIFECYCLE,
    VALIDATION_GUIDES,
    component_for_resource,
)


@dataclass(frozen=True)
class ResourceDetail:
    resource_id: str
    name: str
    resource_type: str
    description: str
    attributes: tuple[tuple[str, str], ...]


def initialize_ui_state() -> None:
    """Initialize only presentation state; the simulation remains stateless."""

    defaults: dict[str, Any] = {
        "view": "landing",
        "guided_tour": False,
        "active_scenario": ScenarioName.NORMAL_OPERATION.value,
        "simulation_result": None,
        "timeline_step": 0,
        "selected_resource": "vpc-main",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_application(project_name: str, simulation_notice: str) -> None:
    apply_theme()
    if st.session_state.view == "landing":
        render_landing_page(project_name, simulation_notice)
    else:
        render_simulator(project_name, simulation_notice)


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #0f172a;
            --muted: #64748b;
            --line: #dbe4f0;
            --panel: rgba(255, 255, 255, 0.94);
            --brand: #2563eb;
            --safe: #059669;
        }
        .stApp {
            background:
                radial-gradient(circle at 10% 0%, rgba(37,99,235,.12), transparent 30rem),
                linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
            color: var(--ink);
        }
        .block-container {
            max-width: 1440px;
            padding-top: 1.35rem;
            padding-bottom: 3rem;
        }
        .hero {
            padding: clamp(2rem, 5vw, 4.5rem);
            border: 1px solid rgba(148,163,184,.3);
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(255,255,255,.98), rgba(239,246,255,.94));
            box-shadow: 0 24px 70px rgba(15,23,42,.11);
            margin: 1rem 0 1.5rem;
        }
        .eyebrow {
            color: var(--brand);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .16em;
            text-transform: uppercase;
        }
        .hero h1 {
            color: var(--ink);
            font-size: clamp(2.15rem, 6vw, 4.25rem);
            line-height: 1.02;
            letter-spacing: -.045em;
            margin: .65rem 0 1rem;
        }
        .hero p {
            color: #475569;
            font-size: clamp(1rem, 2vw, 1.25rem);
            line-height: 1.75;
            max-width: 850px;
        }
        .notice, .timeline-card, .resource-card {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 18px;
            box-shadow: 0 10px 35px rgba(15,23,42,.06);
        }
        .notice {
            padding: 1rem 1.15rem;
            border-left: 5px solid var(--brand);
            margin: .7rem 0 1.25rem;
        }
        .panel-title {
            color: var(--ink);
            font-weight: 800;
            letter-spacing: -.015em;
            margin-bottom: .2rem;
        }
        .metric-label {
            color: var(--muted);
            font-size: .78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .06em;
        }
        .timeline-card {
            padding: .85rem 1rem;
            margin-bottom: .65rem;
        }
        .timeline-current {
            border-color: #60a5fa;
            box-shadow: 0 10px 35px rgba(37,99,235,.14);
        }
        .timeline-time {
            color: var(--brand);
            font-weight: 800;
            font-size: .8rem;
        }
        .resource-card {
            padding: 1rem 1.1rem;
            min-height: 220px;
        }
        .simulated-badge {
            display: inline-flex;
            align-items: center;
            padding: .25rem .65rem;
            border-radius: 999px;
            background: #dbeafe;
            color: #1d4ed8;
            font-size: .75rem;
            font-weight: 800;
        }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,.9);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: .85rem 1rem;
            box-shadow: 0 8px 24px rgba(15,23,42,.05);
        }
        [data-testid="stWidgetLabel"] p,
        [data-testid="stMetricLabel"] p {
            color: #475569 !important;
        }
        [data-testid="stMetricValue"] {
            color: #0f172a !important;
        }
        div[data-testid="stButton"] > button {
            border-radius: 12px;
            font-weight: 750;
            min-height: 2.8rem;
            background: #ffffff !important;
            border-color: #94a3b8 !important;
            color: #0f172a !important;
        }
        div[data-testid="stButton"] > button p,
        div[data-testid="stButton"] > button span {
            color: #0f172a !important;
        }
        div[data-testid="stButton"] > button[kind="primary"] {
            background: #2563eb !important;
            border-color: #2563eb !important;
            color: #ffffff !important;
        }
        div[data-testid="stButton"] > button[kind="primary"] p,
        div[data-testid="stButton"] > button[kind="primary"] span {
            color: #ffffff !important;
        }
        div[data-testid="stButton"] > button:disabled {
            background: #cbd5e1 !important;
            border-color: #cbd5e1 !important;
            color: #64748b !important;
        }
        div[data-testid="stButton"] > button:disabled p,
        div[data-testid="stButton"] > button:disabled span {
            color: #64748b !important;
        }
        button:focus-visible, [role="tab"]:focus-visible,
        input:focus-visible, [role="combobox"]:focus-visible {
            outline: 3px solid #2563eb !important;
            outline-offset: 3px;
        }
        @media (max-width: 760px) {
            .block-container { padding: .75rem .8rem 2rem; }
            .hero { padding: 1.5rem; border-radius: 20px; }
            .hero h1 { font-size: 2.2rem; }
            [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                min-width: min(100%, 19rem) !important;
                flex: 1 1 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_landing_page(project_name: str, simulation_notice: str) -> None:
    st.markdown(
        f"""
        <section class="hero">
          <div class="eyebrow">Interactive cloud engineering portfolio</div>
          <h1>{escape(project_name)}</h1>
          <p>
            Explore how a production-shaped AWS environment routes traffic,
            detects failures, scales capacity, and recovers across Availability Zones.
            Every transition is deterministic, educational, and safe to replay.
          </p>
          <span class="simulated-badge">100% OFFLINE SIMULATION</span>
        </section>
        """,
        unsafe_allow_html=True,
    )
    render_simulation_notice(simulation_notice)
    primary, secondary, _ = st.columns([1, 1, 2])
    with primary:
        if st.button(
            "Start Guided Tour",
            type="primary",
            width="stretch",
            key="start_guided_tour",
        ):
            _open_simulator(ScenarioName.INSTANCE_FAILURE, guided=True)
            st.rerun()
    with secondary:
        if st.button(
            "Open Simulator",
            width="stretch",
            key="open_simulator",
        ):
            _open_simulator(ScenarioName.NORMAL_OPERATION, guided=False)
            st.rerun()

    st.markdown("### What this experience demonstrates")
    cards = st.columns(4)
    content = (
        ("Multi-AZ design", "Public and private subnets across two isolated zones."),
        ("Automatic recovery", "Health checks remove failed targets and restore capacity."),
        ("Elastic capacity", "Traffic pressure triggers deterministic scale out and scale in."),
        ("Observable systems", "Metrics, alarm states, and event history explain every decision."),
    )
    for column, (title, body) in zip(cards, content):
        with column:
            st.markdown(
                f'<div class="resource-card"><div class="panel-title">{title}</div>'
                f"<p>{body}</p></div>",
                unsafe_allow_html=True,
            )


def render_simulation_notice(simulation_notice: str) -> None:
    st.markdown(
        f'<div class="notice"><strong>Simulation-only environment</strong><br>'
        f"{escape(simulation_notice)} No metrics on this page come from AWS.</div>",
        unsafe_allow_html=True,
    )


def render_simulator(project_name: str, simulation_notice: str) -> None:
    architecture = build_reference_architecture()
    result = _active_result()
    step = min(st.session_state.timeline_step, len(result.events))
    snapshot = result.snapshots[step]

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.caption("CLOUD INFRASTRUCTURE LAB / OFFLINE")
        st.title(project_name)
    with top_right:
        if st.button(
            "Reset Simulation",
            width="stretch",
            key="reset_simulation",
            help="Return the current scenario to its initial simulated state.",
        ):
            st.session_state.timeline_step = 0
            st.rerun()
    render_simulation_notice(simulation_notice)

    if st.session_state.guided_tour:
        render_guided_tour(step, len(result.events))

    overview, monitoring, security, costs, learn, terraform = st.tabs(
        [
            "Overview",
            "Monitoring",
            "Security Review",
            "Cost Awareness",
            "Learn",
            "Terraform Explorer",
        ]
    )
    with overview:
        controls, main = st.columns([1, 2.15], gap="large")
        with controls:
            render_scenario_controls(result)
            render_infrastructure_status(snapshot)
            render_alarm_panel(snapshot)
        with main:
            render_architecture_view(architecture, snapshot)
            render_metrics_dashboard(snapshot)

        details, timeline = st.columns([1, 1.35], gap="large")
        with details:
            render_resource_details(architecture, snapshot)
        with timeline:
            render_timeline(result, step)
    with monitoring:
        render_monitoring_dashboard(result, step)
    with security:
        render_security_review_panel()
    with costs:
        render_cost_awareness_panel()
    with learn:
        render_educational_mode()
    with terraform:
        render_terraform_explorer(architecture, snapshot)


def render_monitoring_dashboard(result: SimulationResult, step: int) -> None:
    """Render deterministic CloudWatch-style telemetry through the current event."""

    view = build_monitoring_view(result, step)
    st.subheader("Monitoring dashboard")
    st.info(
        "Simulated CloudWatch-style telemetry — no AWS account is connected and "
        "no live CloudWatch data is queried."
    )
    cpu, requests, hosts, latency = st.columns(4)
    cpu.metric("CPU utilization", f"{view.current.cpu_utilization_percent:.1f}%")
    requests.metric("Request rate", f"{view.current.request_rate:,} req/min")
    hosts.metric("Healthy host count", str(view.current.healthy_host_count))
    latency.metric("Response time", f"{view.current.response_time_ms:.1f} ms")

    if view.recovery_status in {"Recovery complete", "Healthy and stable"}:
        st.success(f"Recovery status: {view.recovery_status}")
    else:
        st.info(f"Recovery status: {view.recovery_status}")

    metric_rows = [
        {
            "Event time": point.timestamp,
            "CPU utilization (%)": point.cpu_utilization_percent,
            "Response time (ms)": point.response_time_ms,
        }
        for point in view.history
    ]
    traffic_rows = [
        {
            "Event time": point.timestamp,
            "Request rate (req/min)": point.request_rate,
            "Healthy hosts": point.healthy_host_count,
        }
        for point in view.history
    ]
    left, right = st.columns(2)
    with left:
        st.markdown("#### Performance history")
        st.line_chart(metric_rows, x="Event time")
    with right:
        st.markdown("#### Traffic and capacity history")
        st.line_chart(traffic_rows, x="Event time")

    active, history = st.columns(2)
    with active:
        st.markdown("#### Active alarms")
        if view.active_alarm_ids:
            for alarm_id in view.active_alarm_ids:
                st.error(f"ALARM · {alarm_id}")
        else:
            st.success("No active alarms at this timeline step.")
    with history:
        st.markdown("#### Alarm history")
        if view.alarm_history:
            for transition in reversed(view.alarm_history):
                st.markdown(
                    f"**t+{transition.timestamp}s · {transition.alarm_id}**  \n"
                    f"{transition.previous_state.value} → "
                    f"{transition.current_state.value}"
                )
        else:
            st.caption("No alarm state changes have occurred yet.")


def render_security_review_panel() -> None:
    """Explain the reference design's reviewed security boundaries."""

    st.subheader("Security review")
    st.info(
        "Static educational review of the simulated design. This is not a live "
        "AWS security scan."
    )
    st.graphviz_chart(build_security_review_dot(), width="stretch")
    st.markdown("#### Reviewed controls")
    for control in SECURITY_CONTROLS:
        with st.expander(control.name):
            st.markdown(f"**How it is implemented:** {control.implementation}")
            st.markdown(f"**Why this decision was made:** {control.reason}")
            st.caption(f"Design evidence: {control.evidence}")

    st.markdown("#### Security best-practice checklist")
    for item in (
        "Keep compute private and expose one managed entry point.",
        "Use security-group references for service-to-service trust.",
        "Use temporary IAM role credentials with resource-scoped permissions.",
        "Require IMDSv2 and encrypted EBS in the production launch template.",
        "Block public S3 access, encrypt objects, and retain useful versions.",
        "Send actionable alarms and logs to an owned operational workflow.",
    ):
        st.markdown(f"- {item}")

    st.markdown("#### Common misconfiguration examples")
    for example in MISCONFIGURATIONS:
        with st.expander(example.name):
            st.warning(f"Risk: {example.risk}")
            st.markdown(f"**Safer design:** {example.safer_design}")


def render_cost_awareness_panel() -> None:
    """Present dated static estimates without any pricing service dependency."""

    st.subheader("Cost awareness")
    st.warning(
        f"{ESTIMATE_DISCLAIMER} Assumptions shown for {ESTIMATE_REGION}, "
        f"dated {ESTIMATE_DATE}. No AWS Pricing API is used."
    )
    total = estimated_monthly_total()
    largest = max(PRODUCTION_COST_ESTIMATES, key=lambda item: item.estimated_monthly_usd)
    total_col, largest_col, simulator_col = st.columns(3)
    total_col.metric("Example production total", f"${total:,.2f}/month")
    largest_col.metric("Largest example item", largest.service)
    simulator_col.metric("This simulator's AWS cost", "$0.00")
    st.caption(
        "Every amount is an educational estimate. The total excludes variable "
        "ALB capacity units, NAT processing, logs, taxes, and other workload usage."
    )

    for estimate in PRODUCTION_COST_ESTIMATES:
        with st.expander(
            f"{estimate.service} · estimated ${estimate.estimated_monthly_usd:,.2f}/month"
        ):
            st.markdown(f"**Example usage:** {estimate.example_usage}")
            st.markdown(f"**Rate assumption:** {estimate.unit_assumption}")
            st.markdown(f"**Main cost driver:** {estimate.cost_driver}")
            st.markdown(f"**Cost-aware practice:** {estimate.optimization}")

    st.success(
        "Portfolio strategy: keep this offline simulator permanently available "
        "instead of leaving chargeable AWS infrastructure running."
    )


def render_educational_mode() -> None:
    """Provide consistent explanations and interview prompts for each component."""

    st.subheader("Educational mode")
    st.info(
        "Choose a component to learn what it does, why the architecture needs it, "
        "and how to discuss it in an interview."
    )
    guide_by_id = {guide.component_id: guide for guide in COMPONENT_GUIDES}
    selected_id = st.selectbox(
        "AWS component",
        options=list(guide_by_id),
        format_func=lambda item: guide_by_id[item].name,
        key="education_component",
    )
    guide = guide_by_id[selected_id]
    st.markdown(f"### {guide.name}")
    st.markdown(f"**What it is:** {guide.what_it_is}")
    st.markdown(f"**Why it exists here:** {guide.why_it_exists}")
    st.markdown("**Best practices**")
    for practice in guide.best_practices:
        st.markdown(f"- {practice}")
    st.success(f"Interview tip: {guide.interview_tip}")


def render_terraform_explorer(
    architecture: ArchitectureState, snapshot: SimulationSnapshot
) -> None:
    """Render static HCL and map the current simulator selection to it."""

    st.subheader("Terraform Explorer")
    st.info(
        "Offline educational content only. Terraform is never executed, AWS is "
        "never contacted, and no credentials or provider authentication are required."
    )
    details = build_resource_details(architecture, snapshot)
    detail_by_id = {item.resource_id: item for item in details}
    selected_resource_id = st.session_state.selected_resource
    selected_resource = detail_by_id.get(selected_resource_id, details[0])
    mapped_component = component_for_resource(
        selected_resource.resource_id, selected_resource.resource_type
    )
    if st.session_state.get("terraform_mapped_resource") != selected_resource.resource_id:
        st.session_state.terraform_component = mapped_component
        st.session_state.terraform_mapped_resource = selected_resource.resource_id

    example_ids = [item.component_id for item in TERRAFORM_EXAMPLES]
    selected_component = st.selectbox(
        "Explore Terraform by component",
        options=example_ids,
        format_func=lambda item: TERRAFORM_EXAMPLE_BY_ID[item].name,
        key="terraform_component",
    )
    example = TERRAFORM_EXAMPLE_BY_ID[selected_component]
    st.caption(
        f"Simulator mapping: {selected_resource.resource_type} · "
        f"{selected_resource.name} → {example.name}"
    )
    st.code(example.hcl, language="hcl", line_numbers=True)

    explanation, dependencies = st.columns(2)
    with explanation:
        st.markdown("#### Resource explanation")
        st.write(example.explanation)
        st.markdown("**Important arguments**")
        for argument in example.important_arguments:
            st.markdown(f"- `{argument}`")
    with dependencies:
        st.markdown("#### Dependencies")
        for dependency in example.dependencies:
            st.markdown(f"- {dependency}")
        st.markdown("#### Security considerations")
        for consideration in example.security_considerations:
            st.markdown(f"- {consideration}")
        st.markdown("#### Best practices")
        for practice in example.best_practices:
            st.markdown(f"- {practice}")

    st.divider()
    render_terraform_lifecycle()
    render_production_demo_comparison()
    render_terraform_validation()


def render_terraform_lifecycle() -> None:
    """Visualize Terraform's workflow without invoking its executable."""

    st.markdown("### Terraform lifecycle")
    st.caption(
        "Demonstration sequence only. No command shown below runs in this application."
    )
    for index, step in enumerate(TERRAFORM_LIFECYCLE, start=1):
        with st.expander(f"{index}. {step.command}"):
            st.write(step.purpose)
            if step.changes_infrastructure:
                st.warning(step.educational_output)
            else:
                st.success(step.educational_output)


def render_production_demo_comparison() -> None:
    """Explain why the simulator differs from deployable infrastructure."""

    st.markdown("### Production architecture vs educational simulator")
    production, simulator = st.columns(2)
    with production:
        st.markdown("#### Production architecture")
        for topic, production_value, _ in PRODUCTION_DEMO_COMPARISON:
            st.markdown(f"**{topic}:** {production_value}")
    with simulator:
        st.markdown("#### Educational simulator")
        for topic, _, simulator_value in PRODUCTION_DEMO_COMPARISON:
            st.markdown(f"**{topic}:** {simulator_value}")
    st.success(
        "The simulator remains completely free because it creates no AWS resources, "
        "stores no remote state, and sends no cloud or network requests."
    )


def render_terraform_validation() -> None:
    """Describe offline validation tools using explicitly simulated output."""

    st.markdown("### Validation and security checks")
    st.warning(
        "Educational output only. Terraform, TFLint, Checkov, and Trivy are not "
        "installed, called, or executed by this application."
    )
    for tool, explanation, output in VALIDATION_GUIDES:
        with st.expander(tool):
            st.write(explanation)
            st.code(output, language="text")


def build_security_review_dot() -> str:
    """Return the fixed trust-path diagram used by the educational security review."""

    return """
digraph security_review {
  graph [rankdir=LR, bgcolor="transparent", pad=0.25, nodesep=0.35];
  node [shape=box, style="rounded,filled", fontname="Arial", color="#94a3b8",
        fillcolor="#ffffff", fontcolor="#0f172a", margin=0.16];
  edge [color="#2563eb", fontname="Arial", fontsize=9, fontcolor="#475569"];
  internet [label="Internet", shape=oval, fillcolor="#dbeafe"];
  alb [label="Public ALB\\nHTTPS entry point"];
  sg [label="Security-group trust\\nALB → app:8080"];
  ec2 [label="Private EC2\\nNo public IP / no SSH", fillcolor="#dcfce7"];
  iam [label="Least-privilege IAM\\ns3:GetObject prefix"];
  s3 [label="Private encrypted S3\\nPublic access blocked"];
  cw [label="CloudWatch-style\\nmetrics + alarms", fillcolor="#fef3c7"];
  internet -> alb [label="controlled ingress"];
  alb -> sg [label="health + traffic"];
  sg -> ec2 [label="only approved path"];
  ec2 -> iam [label="temporary role"];
  iam -> s3 [label="scoped read"];
  ec2 -> cw [style=dashed, label="observability"];
}
"""


def render_scenario_controls(result: SimulationResult) -> None:
    st.subheader("Scenario controls")
    definitions = available_scenarios()
    label_by_name = {item.name.value: item.title for item in definitions}
    selected = st.selectbox(
        "Choose a scenario",
        options=[item.name.value for item in definitions],
        format_func=label_by_name.get,
        key="scenario_selector",
        help="Choose a safe, deterministic infrastructure event to replay.",
    )
    definition = SCENARIOS[ScenarioName(selected)]
    st.caption(definition.summary)
    if st.button(
        "Run selected scenario",
        type="primary",
        width="stretch",
        key="run_selected_scenario",
    ):
        st.session_state.active_scenario = selected
        st.session_state.simulation_result = run_scenario(selected)
        st.session_state.timeline_step = 0
        st.rerun()

    total = len(result.events)
    current = min(st.session_state.timeline_step, total)
    st.progress(current / total if total else 1.0, text=f"Event {current} of {total}")
    previous, next_event = st.columns(2)
    with previous:
        if st.button(
            "Previous",
            disabled=current == 0,
            width="stretch",
            key="previous_event",
        ):
            st.session_state.timeline_step = current - 1
            st.rerun()
    with next_event:
        if st.button(
            "Next event",
            disabled=current >= total,
            width="stretch",
            key="next_event",
        ):
            st.session_state.timeline_step = current + 1
            st.rerun()


def render_guided_tour(step: int, total_events: int) -> None:
    if step == 0:
        message = (
            "Begin with the healthy two-zone design. Select Next event to fail one "
            "instance and follow the recovery sequence."
        )
    elif step < total_events:
        message = (
            "Follow the highlighted timeline event, architecture colors, metrics, "
            "and alarms. Select Next event when you are ready."
        )
    else:
        message = (
            "Tour complete: health checks protected traffic while Auto Scaling "
            "restored multi-zone capacity."
        )
    st.info(f"Guided Tour - {message}")


def render_architecture_view(
    architecture: ArchitectureState, snapshot: SimulationSnapshot
) -> None:
    st.subheader("Interactive architecture")
    st.caption(
        "Simulated topology at the selected event. Choose any resource below to inspect it."
    )
    st.graphviz_chart(
        build_architecture_dot(architecture, snapshot),
        width="stretch",
    )


def render_metrics_dashboard(snapshot: SimulationSnapshot) -> None:
    st.subheader("Simulated metrics")
    healthy = sum(item.health.value == "healthy" for item in snapshot.instances)
    average_cpu = (
        sum(item.cpu_utilization_percent for item in snapshot.instances)
        / len(snapshot.instances)
        if snapshot.instances
        else 0.0
    )
    metrics = (
        ("Requests / interval", str(snapshot.request_rate)),
        ("Healthy targets", f"{healthy}/{len(snapshot.instances)}"),
        ("Desired capacity", str(snapshot.desired_capacity)),
        ("Average CPU", f"{average_cpu:.1f}%"),
    )
    columns = st.columns(4)
    for column, (label, value) in zip(columns, metrics):
        column.metric(label, value, help="Simulated metric - no AWS data is queried.")


def render_infrastructure_status(snapshot: SimulationSnapshot) -> None:
    st.subheader("Infrastructure status")
    healthy_targets = sum(item.health.value == "healthy" for item in snapshot.instances)
    status_rows = (
        ("Load balancer", snapshot.load_balancer_status.value),
        ("Target group", snapshot.target_group_status.value),
        ("Healthy instances", f"{healthy_targets}/{len(snapshot.instances)}"),
        ("Unavailable zones", ", ".join(sorted(snapshot.unavailable_zones)) or "None"),
    )
    for label, value in status_rows:
        st.markdown(f"**{label}:** `{value}`")
    st.caption("All resource states shown here are simulated.")


def render_alarm_panel(snapshot: SimulationSnapshot) -> None:
    st.subheader("CloudWatch-style alarms")
    for alarm in snapshot.alarms:
        if alarm.state is AlarmState.ALARM:
            st.error(f"{alarm.resource_id}: ALARM")
        elif alarm.state is AlarmState.INSUFFICIENT_DATA:
            st.warning(f"{alarm.resource_id}: INSUFFICIENT DATA")
        else:
            st.success(f"{alarm.resource_id}: OK")
    st.caption("Educational alarm states only; CloudWatch is not contacted.")


def render_timeline(result: SimulationResult, step: int) -> None:
    st.subheader("Event timeline")
    if step == 0:
        st.info("The architecture is at its initial snapshot. Select Next event to begin.")
        return
    for index, event in enumerate(result.events[:step], start=1):
        current_class = " timeline-current" if index == step else ""
        st.markdown(
            f'<div class="timeline-card{current_class}">'
            f'<div class="timeline-time">T+{event.timestamp:02d}s · '
            f"{escape(event.event_type.value.replace('_', ' ').upper())}</div>"
            f"<strong>{escape(event.affected_resource)}</strong><br>"
            f"{escape(event.explanation)}</div>",
            unsafe_allow_html=True,
        )


def render_resource_details(
    architecture: ArchitectureState, snapshot: SimulationSnapshot
) -> None:
    st.subheader("Resource explorer")
    details = build_resource_details(architecture, snapshot)
    detail_by_id = {item.resource_id: item for item in details}
    resource_ids = list(detail_by_id)
    if st.session_state.selected_resource not in detail_by_id:
        st.session_state.selected_resource = resource_ids[0]
    selected_id = st.selectbox(
        "Select any architecture resource",
        options=resource_ids,
        format_func=lambda value: (
            f"{detail_by_id[value].resource_type} · {detail_by_id[value].name}"
        ),
        key="selected_resource",
        help="Inspect the resource here and see its matching HCL in Terraform Explorer.",
    )
    selected = detail_by_id[selected_id]
    rows = "".join(
        f"<div><span class='metric-label'>{escape(label)}</span><br>"
        f"<strong>{escape(value)}</strong></div><br>"
        for label, value in selected.attributes
    )
    st.markdown(
        f'<div class="resource-card"><span class="simulated-badge">'
        f"{escape(selected.resource_type)}</span>"
        f"<h3>{escape(selected.name)}</h3><p>{escape(selected.description)}</p>"
        f"{rows}</div>",
        unsafe_allow_html=True,
    )


def build_resource_details(
    architecture: ArchitectureState, snapshot: SimulationSnapshot
) -> tuple[ResourceDetail, ...]:
    """Return every static and dynamic architecture resource for selection."""

    details = [
        ResourceDetail(
            architecture.vpc.resource_id,
            architecture.vpc.name,
            "VPC",
            "The isolated regional network boundary for the simulated environment.",
            (
                ("CIDR", architecture.vpc.cidr_block),
                ("Region", architecture.vpc.region),
                ("DNS", "Enabled"),
            ),
        ),
        ResourceDetail(
            architecture.internet_gateway.resource_id,
            architecture.internet_gateway.name,
            "Internet Gateway",
            "Provides the public subnets with a route to simulated internet users.",
            (("Attached VPC", architecture.internet_gateway.vpc_id),),
        ),
        ResourceDetail(
            architecture.load_balancer.resource_id,
            architecture.load_balancer.name,
            "Application Load Balancer",
            "Accepts public requests and forwards them only to healthy targets.",
            (
                ("Status", snapshot.load_balancer_status.value),
                ("Scheme", architecture.load_balancer.scheme),
                (
                    "Listener",
                    (
                        f"{architecture.load_balancer.listener_protocol} "
                        f":{architecture.load_balancer.listener_port}"
                    ),
                ),
            ),
        ),
        ResourceDetail(
            architecture.target_group.resource_id,
            architecture.target_group.name,
            "Target Group",
            "Tracks application instances and evaluates their /health responses.",
            (
                ("Status", snapshot.target_group_status.value),
                ("Health path", architecture.target_group.health_check_path),
                ("Registered targets", str(len(snapshot.registered_target_ids))),
            ),
        ),
        ResourceDetail(
            architecture.auto_scaling_group.resource_id,
            architecture.auto_scaling_group.name,
            "Auto Scaling Group",
            "Maintains healthy capacity across private subnets in two zones.",
            (
                ("Desired", str(snapshot.desired_capacity)),
                ("Minimum", str(architecture.auto_scaling_group.minimum_capacity)),
                ("Maximum", str(architecture.auto_scaling_group.maximum_capacity)),
            ),
        ),
        ResourceDetail(
            architecture.iam_role.resource_id,
            architecture.iam_role.name,
            "IAM Role",
            "Demonstrates EC2 least-privilege access to one private S3 prefix.",
            (
                ("Trusted service", architecture.iam_role.assumed_by_service),
                ("Allowed action", "s3:GetObject"),
            ),
        ),
        ResourceDetail(
            architecture.s3_bucket.resource_id,
            architecture.s3_bucket.name,
            "S3 Bucket",
            "Represents encrypted, versioned, non-public artifact storage.",
            (
                ("Encryption", architecture.s3_bucket.encryption),
                ("Public access", "Blocked"),
                ("Versioning", "Enabled"),
            ),
        ),
    ]
    details.extend(
        ResourceDetail(
            item.resource_id,
            item.name,
            "Subnet",
            "Places load-balancing or application resources within one Availability Zone.",
            (
                ("Type", item.subnet_type.value),
                ("Availability Zone", item.availability_zone),
                ("CIDR", item.cidr_block),
            ),
        )
        for item in architecture.subnets
    )
    details.extend(
        ResourceDetail(
            item.resource_id,
            item.name,
            "Route Table",
            "Controls the simulated paths available to associated subnets.",
            (
                ("Associated subnets", str(len(item.associated_subnet_ids))),
                ("Routes", str(len(item.routes))),
            ),
        )
        for item in architecture.route_tables
    )
    details.extend(
        ResourceDetail(
            item.resource_id,
            item.name,
            "Security Group",
            item.description,
            (
                ("Inbound rules", str(len(item.inbound_rules))),
                ("Outbound rules", str(len(item.outbound_rules))),
            ),
        )
        for item in architecture.security_groups
    )
    details.extend(
        ResourceDetail(
            item.resource_id,
            item.resource_id,
            "EC2 Instance",
            "A private application target managed by the simulated Auto Scaling Group.",
            (
                ("Availability Zone", item.availability_zone),
                ("Lifecycle", item.lifecycle.value),
                ("Health", item.health.value),
                ("CPU", f"{item.cpu_utilization_percent:.1f}%"),
            ),
        )
        for item in snapshot.instances
    )
    alarm_states = {item.resource_id: item.state.value for item in snapshot.alarms}
    details.extend(
        ResourceDetail(
            item.resource_id,
            item.name,
            "CloudWatch Alarm",
            item.description,
            (
                ("Metric", item.metric_name),
                ("Threshold", str(item.threshold)),
                ("State", alarm_states[item.resource_id]),
            ),
        )
        for item in architecture.cloudwatch.alarms
    )
    return tuple(details)


def build_architecture_dot(
    architecture: ArchitectureState, snapshot: SimulationSnapshot
) -> str:
    """Create a deterministic Graphviz diagram for the selected snapshot."""

    instance_by_subnet: dict[str, list[Any]] = {}
    for instance in snapshot.instances:
        instance_by_subnet.setdefault(instance.subnet_id, []).append(instance)

    def color(status: str) -> str:
        return {
            "healthy": "#10b981",
            "degraded": "#f59e0b",
            "unhealthy": "#ef4444",
            "unavailable": "#94a3b8",
        }.get(status, "#3b82f6")

    lines = [
        "digraph architecture {",
        'graph [rankdir=TB, bgcolor="transparent", pad="0.25", nodesep="0.35", ranksep="0.5"];',
        'node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10, color="#cbd5e1", fontcolor="#0f172a", fillcolor="#ffffff", margin="0.14,0.09"];',
        'edge [color="#64748b", fontname="Arial", fontsize=8, arrowsize=0.7];',
        '"internet" [label="Internet users", shape=oval, fillcolor="#dbeafe"];',
        '"igw-main" [label="Internet Gateway", fillcolor="#e0f2fe"];',
        f'"alb-public" [label="Application Load Balancer\\n{snapshot.load_balancer_status.value}", fillcolor="{color(snapshot.load_balancer_status.value)}", fontcolor="white"];',
        '"internet" -> "igw-main" [label="simulated requests"];',
        '"igw-main" -> "alb-public";',
        'subgraph cluster_vpc { label="VPC 10.20.0.0/16 · us-east-1"; color="#93c5fd"; style="rounded,dashed";',
    ]
    for zone in ("us-east-1a", "us-east-1b"):
        zone_status = "unavailable" if zone in snapshot.unavailable_zones else "healthy"
        lines.append(
            f'subgraph "cluster_{zone}" {{ label="{zone}\\n{zone_status}"; '
            f'color="{color(zone_status)}"; style="rounded";'
        )
        for subnet in [
            item for item in architecture.subnets if item.availability_zone == zone
        ]:
            subnet_fill = (
                "#e0f2fe"
                if subnet.subnet_type is SubnetType.PUBLIC
                else "#ede9fe"
            )
            lines.append(
                f'"{subnet.resource_id}" [label="{subnet.name}\\n{subnet.cidr_block}", '
                f'fillcolor="{subnet_fill}"];'
            )
            for instance in instance_by_subnet.get(subnet.resource_id, []):
                lines.append(
                    f'"{instance.resource_id}" [label="{instance.resource_id}\\n'
                    f'{instance.health.value}", fillcolor="{color(instance.health.value)}", '
                    'fontcolor="white"];'
                )
                lines.append(
                    f'"{subnet.resource_id}" -> "{instance.resource_id}" [label="hosts"];'
                )
        lines.append("}")
    lines.extend(
        [
            f'"tg-app" [label="Target Group\\n{len(snapshot.registered_target_ids)} registered", fillcolor="#fef3c7"];',
            f'"asg-app" [label="Auto Scaling Group\\ndesired {snapshot.desired_capacity}", fillcolor="#d1fae5"];',
            '"s3-artifacts" [label="Private S3 Bucket", fillcolor="#fef3c7"];',
            '"iam-app-role" [label="Least-privilege IAM Role", fillcolor="#fee2e2"];',
            "}",
            '"alb-public" -> "tg-app" [label="forwards"];',
            '"asg-app" -> "tg-app" [label="registers"];',
            '"iam-app-role" -> "s3-artifacts" [label="scoped read"];',
        ]
    )
    for instance_id in snapshot.registered_target_ids:
        lines.append(f'"tg-app" -> "{instance_id}" [label="/health"];')
    lines.append("}")
    return "\n".join(lines)


def _open_simulator(scenario: ScenarioName, guided: bool) -> None:
    st.session_state.view = "simulator"
    st.session_state.guided_tour = guided
    st.session_state.active_scenario = scenario.value
    st.session_state.simulation_result = run_scenario(scenario)
    st.session_state.timeline_step = 0
    st.session_state.scenario_selector = scenario.value


def _active_result() -> SimulationResult:
    result = st.session_state.get("simulation_result")
    if isinstance(result, SimulationResult):
        return result
    scenario = st.session_state.get(
        "active_scenario", ScenarioName.NORMAL_OPERATION.value
    )
    try:
        result = run_scenario(scenario)
    except ValueError:
        scenario = ScenarioName.NORMAL_OPERATION.value
        result = run_scenario(scenario)
        st.session_state.active_scenario = scenario
        st.session_state.scenario_selector = scenario
    st.session_state.simulation_result = result
    return result
