from pathlib import Path

from src.architecture import build_reference_architecture
from src.scenarios import ScenarioName, run_scenario
from src.terraform_explorer import (
    PRODUCTION_DEMO_COMPARISON,
    TERRAFORM_EXAMPLE_BY_ID,
    TERRAFORM_EXAMPLES,
    TERRAFORM_LIFECYCLE,
    VALIDATION_GUIDES,
    component_for_resource,
)
from src.ui import build_resource_details

EXPECTED_COMPONENTS = {
    "vpc",
    "internet-gateway",
    "route-tables",
    "public-subnets",
    "private-subnets",
    "security-groups",
    "alb",
    "target-group",
    "auto-scaling-group",
    "launch-template",
    "ec2",
    "iam",
    "s3",
    "cloudwatch",
}


def test_explorer_contains_every_requested_component():
    assert {item.component_id for item in TERRAFORM_EXAMPLES} == EXPECTED_COMPONENTS
    assert set(TERRAFORM_EXAMPLE_BY_ID) == EXPECTED_COMPONENTS


def test_every_example_has_hcl_and_complete_learning_metadata():
    for example in TERRAFORM_EXAMPLES:
        assert 'resource "' in example.hcl or example.component_id == "ec2"
        assert example.explanation
        assert example.important_arguments
        assert example.dependencies
        assert example.security_considerations
        assert example.best_practices


def test_every_selectable_simulator_resource_maps_to_terraform():
    architecture = build_reference_architecture()
    snapshot = run_scenario(ScenarioName.TRAFFIC_SPIKE).snapshots[-1]
    details = build_resource_details(architecture, snapshot)

    mapped = {
        component_for_resource(detail.resource_id, detail.resource_type)
        for detail in details
    }

    assert mapped <= EXPECTED_COMPONENTS
    assert {
        "vpc",
        "internet-gateway",
        "route-tables",
        "public-subnets",
        "private-subnets",
        "security-groups",
        "alb",
        "target-group",
        "auto-scaling-group",
        "ec2",
        "iam",
        "s3",
        "cloudwatch",
    } <= mapped


def test_specific_dynamic_and_subnet_resource_mappings_are_correct():
    assert component_for_resource("subnet-public-a", "Public Subnet") == "public-subnets"
    assert component_for_resource("subnet-private-b", "Private Subnet") == "private-subnets"
    assert component_for_resource("i-replacement", "EC2 Instance") == "ec2"
    assert component_for_resource("alarm-high-cpu", "CloudWatch Alarm") == "cloudwatch"


def test_lifecycle_is_complete_and_apply_destroy_are_clearly_mutating():
    commands = [step.command for step in TERRAFORM_LIFECYCLE]

    for expected in (
        "terraform init",
        "terraform validate",
        "terraform fmt -check",
        "terraform plan",
        "terraform apply",
        "terraform destroy",
    ):
        assert expected in commands
    assert {
        step.command for step in TERRAFORM_LIFECYCLE if step.changes_infrastructure
    } == {"terraform apply", "terraform destroy"}
    assert all(step.purpose and step.educational_output for step in TERRAFORM_LIFECYCLE)


def test_validation_and_production_comparison_content_is_complete():
    validation_names = {item[0] for item in VALIDATION_GUIDES}

    assert validation_names == {
        "terraform fmt",
        "terraform validate",
        "TFLint",
        "Checkov / Trivy",
    }
    assert len(PRODUCTION_DEMO_COMPARISON) >= 6
    assert all(all(column for column in row) for row in PRODUCTION_DEMO_COMPARISON)


def test_terraform_explorer_has_no_execution_or_network_path():
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        (root / path).read_text(encoding="utf-8").lower()
        for path in ("src/terraform_explorer.py", "src/ui.py")
    )
    forbidden = (
        "import boto3",
        "import requests",
        "import subprocess",
        "import socket",
        "os.system",
        "popen(",
        "terraform.exe",
        "http://",
        "https://",
        "aws_access_key",
        "aws_secret",
    )

    assert all(term not in source for term in forbidden)
