from pathlib import Path

from src.cost_data import PRODUCTION_COST_ESTIMATES, estimated_monthly_total
from src.education import COMPONENT_GUIDES, MISCONFIGURATIONS, SECURITY_CONTROLS
from src.ui import build_security_review_dot


def test_educational_mode_covers_every_major_component():
    component_ids = {item.component_id for item in COMPONENT_GUIDES}

    assert component_ids == {
        "vpc",
        "internet-gateway",
        "route-tables",
        "public-subnets",
        "private-subnets",
        "alb",
        "target-group",
        "asg",
        "ec2",
        "security-groups",
        "iam",
        "s3",
        "cloudwatch",
    }
    assert all(
        guide.what_it_is
        and guide.why_it_exists
        and guide.best_practices
        and guide.interview_tip
        for guide in COMPONENT_GUIDES
    )


def test_security_review_covers_requested_controls_and_reasoning():
    names = " ".join(item.name.lower() for item in SECURITY_CONTROLS)

    for expected in (
        "vpc isolation",
        "public and private",
        "security-group",
        "least-privilege",
        "private ec2",
        "alb-only",
        "encrypted private s3",
        "imdsv2",
        "no public ssh",
        "encryption at rest",
    ):
        assert expected in names
    assert all(item.implementation and item.reason and item.evidence for item in SECURITY_CONTROLS)
    assert len(MISCONFIGURATIONS) >= 5


def test_security_diagram_visualizes_the_controlled_trust_path():
    dot = build_security_review_dot()

    for expected in ("Internet", "Public ALB", "Private EC2", "IAM", "encrypted S3"):
        assert expected in dot
    assert "No public IP / no SSH" in dot


def test_cost_estimates_cover_requested_charge_categories():
    services = {item.service for item in PRODUCTION_COST_ESTIMATES}

    assert services == {
        "NAT Gateway",
        "Application Load Balancer",
        "EC2",
        "EBS",
        "CloudWatch",
        "Public IPv4",
        "Data Transfer",
    }
    assert estimated_monthly_total() == 114.39
    assert all(item.estimated_monthly_usd >= 0 for item in PRODUCTION_COST_ESTIMATES)


def test_phase_five_data_sources_are_static_and_offline():
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        (root / path).read_text(encoding="utf-8").lower()
        for path in ("src/monitoring.py", "src/education.py", "src/cost_data.py")
    )

    for forbidden in (
        "import boto3",
        "import requests",
        "boto3.client(",
        "requests.get(",
        "http://",
        "https://",
    ):
        assert forbidden not in source
