from copy import deepcopy

import pytest

from src.architecture import build_reference_architecture
from src.models import IAMPolicyStatement, Route, SecurityRule, SubnetType
from src.validation import (
    ArchitectureValidationError,
    architecture_errors,
    validate_architecture,
)


def test_duplicate_resource_identifiers_are_rejected():
    state = build_reference_architecture()
    state.instances[1].resource_id = state.instances[0].resource_id

    with pytest.raises(ArchitectureValidationError, match="globally unique"):
        validate_architecture(state)


def test_overlapping_subnet_cidrs_are_rejected():
    state = build_reference_architecture()
    state.subnets[1].cidr_block = state.subnets[0].cidr_block

    assert any("overlap" in item for item in architecture_errors(state))


def test_public_subnet_without_internet_route_is_rejected():
    state = build_reference_architecture()
    public_table = next(item for item in state.route_tables if item.resource_id == "rtb-public")
    public_table.routes = [
        route for route in public_table.routes if route.destination_cidr != "0.0.0.0/0"
    ]

    with pytest.raises(ArchitectureValidationError, match="lacks an Internet route"):
        validate_architecture(state)


def test_private_subnet_with_direct_igw_route_is_rejected():
    state = build_reference_architecture()
    private_table = next(
        item for item in state.route_tables if item.resource_id == "rtb-private-a"
    )
    private_table.routes.append(
        Route("0.0.0.0/0", "internet_gateway", state.internet_gateway.resource_id)
    )

    with pytest.raises(ArchitectureValidationError, match="must not route directly"):
        validate_architecture(state)


def test_load_balancer_in_private_subnets_is_rejected():
    state = build_reference_architecture()
    state.load_balancer.subnet_ids = ["subnet-private-a", "subnet-private-b"]

    with pytest.raises(ArchitectureValidationError, match="public subnets"):
        validate_architecture(state)


def test_auto_scaling_group_outside_private_subnets_is_rejected():
    state = build_reference_architecture()
    state.auto_scaling_group.subnet_ids = ["subnet-public-a", "subnet-public-b"]

    with pytest.raises(ArchitectureValidationError, match="only private subnets"):
        validate_architecture(state)


def test_invalid_auto_scaling_capacity_is_rejected():
    state = build_reference_architecture()
    state.auto_scaling_group.minimum_capacity = 3

    with pytest.raises(ArchitectureValidationError, match="min <= desired <= max"):
        validate_architecture(state)


def test_public_ec2_instance_is_rejected():
    state = build_reference_architecture()
    state.instances[0].has_public_ip = True

    with pytest.raises(ArchitectureValidationError, match="must not have a public IP"):
        validate_architecture(state)


def test_ec2_private_ip_outside_its_subnet_is_rejected():
    state = build_reference_architecture()
    state.instances[0].private_ip = "10.20.99.10"

    with pytest.raises(ArchitectureValidationError, match="outside its subnet"):
        validate_architecture(state)


def test_public_application_ingress_is_rejected():
    state = build_reference_architecture()
    app_group = next(item for item in state.security_groups if item.resource_id == "sg-app")
    app_group.inbound_rules.append(
        SecurityRule("Unsafe public application access", "tcp", 8080, 8080, ("0.0.0.0/0",))
    )

    with pytest.raises(ArchitectureValidationError, match="must not allow public ingress"):
        validate_architecture(state)


def test_application_ingress_must_reference_alb_security_group():
    state = build_reference_architecture()
    app_group = next(item for item in state.security_groups if item.resource_id == "sg-app")
    app_group.inbound_rules = [
        SecurityRule(
            "Wrong source",
            "tcp",
            8080,
            8080,
            source_security_group_id="sg-unknown",
        )
    ]

    with pytest.raises(ArchitectureValidationError, match="restricted to the ALB"):
        validate_architecture(state)


@pytest.mark.parametrize(
    "statement",
    [
        IAMPolicyStatement("Allow", ("*",), ("arn:aws:s3:::bucket/*",)),
        IAMPolicyStatement("Allow", ("s3:GetObject",), ("*",)),
        IAMPolicyStatement("Allow", ("ec2:TerminateInstances",), ("arn:aws:ec2:::*",)),
    ],
)
def test_broad_or_unrelated_iam_permissions_are_rejected(statement):
    state = build_reference_architecture()
    state.iam_role.policy_statements = [statement]

    with pytest.raises(ArchitectureValidationError):
        validate_architecture(state)


@pytest.mark.parametrize(
    ("attribute", "value", "message"),
    [
        ("public_access_blocked", False, "block all public access"),
        ("encryption", "", "server-side encryption"),
        ("versioning_enabled", False, "enable versioning"),
        ("lifecycle_expiration_days", 0, "lifecycle period"),
    ],
)
def test_insecure_s3_configuration_is_rejected(attribute, value, message):
    state = build_reference_architecture()
    setattr(state.s3_bucket, attribute, value)

    with pytest.raises(ArchitectureValidationError, match=message):
        validate_architecture(state)


def test_untracked_cloudwatch_alarm_metric_is_rejected():
    state = build_reference_architecture()
    state.cloudwatch.alarms[0].metric_name = "UnknownMetric"

    with pytest.raises(ArchitectureValidationError, match="untracked metric"):
        validate_architecture(state)


def test_deep_copied_state_remains_independent_for_future_simulation():
    original = build_reference_architecture()
    changed = deepcopy(original)
    changed.instances[0].cpu_utilization_percent = 99.0
    changed.subnets[0].subnet_type = SubnetType.PRIVATE

    assert original.instances[0].cpu_utilization_percent == 18.0
    assert original.subnets[0].subnet_type is SubnetType.PUBLIC
