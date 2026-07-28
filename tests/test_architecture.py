from dataclasses import is_dataclass

from src.architecture import build_graph_spec, build_reference_architecture
from src.models import (
    VPC,
    AlarmState,
    ApplicationLoadBalancer,
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureState,
    AutoScalingGroup,
    CloudWatchAlarm,
    CloudWatchResources,
    ComparisonOperator,
    EC2Instance,
    HealthState,
    IAMPolicyStatement,
    IAMRole,
    InstanceLifecycle,
    InternetGateway,
    ResourceStatus,
    Route,
    RouteTable,
    S3Bucket,
    SecurityGroup,
    SecurityRule,
    Subnet,
    SubnetType,
    TargetGroup,
)
from src.validation import architecture_errors, validate_architecture


def test_reference_architecture_is_valid():
    state = build_reference_architecture()

    validate_architecture(state)
    assert architecture_errors(state) == []
    assert isinstance(state, ArchitectureState)


def test_all_resource_models_are_dataclasses():
    model_types = [
        VPC,
        InternetGateway,
        Route,
        RouteTable,
        Subnet,
        SecurityRule,
        SecurityGroup,
        IAMPolicyStatement,
        IAMRole,
        S3Bucket,
        TargetGroup,
        ApplicationLoadBalancer,
        AutoScalingGroup,
        EC2Instance,
        CloudWatchAlarm,
        CloudWatchResources,
        ArchitectureNode,
        ArchitectureEdge,
        ArchitectureState,
    ]

    assert all(is_dataclass(model_type) for model_type in model_types)


def test_vpc_and_internet_gateway_model_the_region_boundary():
    state = build_reference_architecture()

    assert state.vpc.cidr_block == "10.20.0.0/16"
    assert state.vpc.region == "us-east-1"
    assert state.vpc.dns_support is True
    assert state.vpc.dns_hostnames is True
    assert state.vpc.status is ResourceStatus.HEALTHY
    assert state.internet_gateway.vpc_id == state.vpc.resource_id
    assert state.internet_gateway.status is ResourceStatus.HEALTHY


def test_route_tables_separate_public_and_private_routing():
    state = build_reference_architecture()
    public_table = next(item for item in state.route_tables if item.resource_id == "rtb-public")
    private_tables = [
        item for item in state.route_tables if item.resource_id.startswith("rtb-private")
    ]

    assert isinstance(public_table.routes[0], Route)
    assert any(
        route.destination_cidr == "0.0.0.0/0"
        and route.target_type == "internet_gateway"
        for route in public_table.routes
    )
    assert len(private_tables) == 2
    assert all(
        not any(route.destination_cidr == "0.0.0.0/0" for route in table.routes)
        for table in private_tables
    )


def test_public_and_private_subnets_span_two_availability_zones():
    state = build_reference_architecture()

    assert len(state.public_subnets) == 2
    assert len(state.private_subnets) == 2
    assert all(isinstance(item, Subnet) for item in state.subnets)
    assert all(item.is_public for item in state.public_subnets)
    assert all(not item.is_public for item in state.private_subnets)
    assert {item.availability_zone for item in state.public_subnets} == {
        "us-east-1a",
        "us-east-1b",
    }
    assert all(item.subnet_type is SubnetType.PRIVATE for item in state.private_subnets)


def test_security_group_models_reference_each_other():
    state = build_reference_architecture()
    alb_group = next(item for item in state.security_groups if item.resource_id == "sg-alb")
    app_group = next(item for item in state.security_groups if item.resource_id == "sg-app")

    assert isinstance(alb_group, SecurityGroup)
    assert isinstance(alb_group.inbound_rules[0], SecurityRule)
    assert alb_group.inbound_rules[0].cidr_blocks == ("0.0.0.0/0",)
    assert app_group.inbound_rules[0].source_security_group_id == alb_group.resource_id


def test_iam_role_is_scoped_to_reading_one_s3_prefix():
    state = build_reference_architecture()
    statement = state.iam_role.policy_statements[0]

    assert isinstance(state.iam_role, IAMRole)
    assert isinstance(statement, IAMPolicyStatement)
    assert state.iam_role.assumed_by_service == "ec2.amazonaws.com"
    assert statement.effect == "Allow"
    assert statement.actions == ("s3:GetObject",)
    assert statement.resources == (
        "arn:aws:s3:::simulated-private-artifacts/application/*",
    )


def test_s3_bucket_has_secure_storage_defaults():
    bucket = build_reference_architecture().s3_bucket

    assert isinstance(bucket, S3Bucket)
    assert bucket.public_access_blocked is True
    assert bucket.versioning_enabled is True
    assert bucket.encryption == "AES256"
    assert bucket.lifecycle_expiration_days == 30


def test_load_balancer_and_target_group_model_health_checked_routing():
    state = build_reference_architecture()

    assert isinstance(state.load_balancer, ApplicationLoadBalancer)
    assert isinstance(state.target_group, TargetGroup)
    assert state.load_balancer.scheme == "internet-facing"
    assert state.load_balancer.cross_zone_enabled is True
    assert state.load_balancer.target_group_id == state.target_group.resource_id
    assert state.target_group.health_check_path == "/health"
    assert state.target_group.port == 8080
    assert state.target_group.healthy_status_codes == (200,)


def test_auto_scaling_group_models_highly_available_capacity():
    group = build_reference_architecture().auto_scaling_group

    assert isinstance(group, AutoScalingGroup)
    assert (group.minimum_capacity, group.desired_capacity, group.maximum_capacity) == (
        2,
        2,
        4,
    )
    assert group.health_check_type == "ELB"
    assert group.subnet_ids == ["subnet-private-a", "subnet-private-b"]


def test_ec2_instances_are_private_healthy_and_distributed():
    state = build_reference_architecture()

    assert all(isinstance(item, EC2Instance) for item in state.instances)
    assert all(item.has_public_ip is False for item in state.instances)
    assert all(item.lifecycle is InstanceLifecycle.IN_SERVICE for item in state.instances)
    assert all(item.health is HealthState.HEALTHY for item in state.instances)
    assert {item.availability_zone for item in state.instances} == {
        "us-east-1a",
        "us-east-1b",
    }
    assert state.healthy_instances == state.instances


def test_cloudwatch_resources_include_metrics_and_alarm_models():
    cloudwatch = build_reference_architecture().cloudwatch

    assert isinstance(cloudwatch, CloudWatchResources)
    assert len(cloudwatch.alarms) == 3
    assert all(isinstance(item, CloudWatchAlarm) for item in cloudwatch.alarms)
    assert all(item.state is AlarmState.OK for item in cloudwatch.alarms)
    assert {
        item.comparison_operator for item in cloudwatch.alarms
    } == {
        ComparisonOperator.GREATER_THAN_THRESHOLD,
        ComparisonOperator.LESS_THAN_THRESHOLD,
    }


def test_architecture_state_lookup_helpers_return_modeled_resources():
    state = build_reference_architecture()

    assert state.subnet("subnet-private-a").name == "private-subnet-a"
    assert state.instance("i-app-b").private_ip == "10.20.11.10"


def test_graph_spec_is_ready_for_future_graphviz_rendering():
    state = build_reference_architecture()
    nodes, edges = build_graph_spec(state)
    node_ids = {item.node_id for item in nodes}

    assert all(isinstance(item, ArchitectureNode) for item in nodes)
    assert all(isinstance(item, ArchitectureEdge) for item in edges)
    assert state.vpc.resource_id in node_ids
    assert state.load_balancer.resource_id in node_ids
    assert {item.resource_id for item in state.instances}.issubset(node_ids)
    assert {
        item.resource_id for item in state.cloudwatch.alarms
    }.issubset(node_ids)
    assert all(item.source_id in node_ids and item.destination_id in node_ids for item in edges)


def test_enum_values_are_stable_for_future_serialization():
    assert ResourceStatus.HEALTHY.value == "healthy"
    assert SubnetType.PUBLIC.value == "public"
    assert InstanceLifecycle.IN_SERVICE.value == "in_service"
    assert HealthState.UNHEALTHY.value == "unhealthy"
    assert AlarmState.INSUFFICIENT_DATA.value == "INSUFFICIENT_DATA"
