"""Consistency and security validation for the internal architecture state."""

from __future__ import annotations

from ipaddress import ip_address, ip_network

from src.models import ArchitectureState, SubnetType


class ArchitectureValidationError(ValueError):
    """Raised when an architecture violates one or more design invariants."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_architecture(state: ArchitectureState) -> None:
    """Raise a single detailed error when the reference architecture is invalid."""

    errors: list[str] = []
    _validate_identifiers(state, errors)
    _validate_networking(state, errors)
    _validate_load_balancing(state, errors)
    _validate_compute(state, errors)
    _validate_security(state, errors)
    _validate_storage_and_monitoring(state, errors)
    if errors:
        raise ArchitectureValidationError(errors)


def architecture_errors(state: ArchitectureState) -> list[str]:
    """Return validation messages without raising for safe presentation."""

    try:
        validate_architecture(state)
    except ArchitectureValidationError as exc:
        return exc.errors
    return []


def _validate_identifiers(state: ArchitectureState, errors: list[str]) -> None:
    identifiers = [
        state.vpc.resource_id,
        state.internet_gateway.resource_id,
        state.iam_role.resource_id,
        state.s3_bucket.resource_id,
        state.target_group.resource_id,
        state.load_balancer.resource_id,
        state.auto_scaling_group.resource_id,
        *(item.resource_id for item in state.route_tables),
        *(item.resource_id for item in state.subnets),
        *(item.resource_id for item in state.security_groups),
        *(item.resource_id for item in state.instances),
        *(item.resource_id for item in state.cloudwatch.alarms),
    ]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Resource identifiers must be globally unique.")
    if any(not item.strip() for item in identifiers):
        errors.append("Resource identifiers cannot be empty.")


def _validate_networking(state: ArchitectureState, errors: list[str]) -> None:
    try:
        vpc_network = ip_network(state.vpc.cidr_block)
    except ValueError:
        errors.append("The VPC CIDR block is invalid.")
        return

    if state.internet_gateway.vpc_id != state.vpc.resource_id:
        errors.append("The Internet Gateway must be attached to the modeled VPC.")

    subnet_networks = []
    route_table_ids = {item.resource_id for item in state.route_tables}
    for subnet in state.subnets:
        if subnet.vpc_id != state.vpc.resource_id:
            errors.append(f"Subnet {subnet.resource_id} belongs to an unknown VPC.")
        if subnet.route_table_id not in route_table_ids:
            errors.append(f"Subnet {subnet.resource_id} references an unknown route table.")
        try:
            network = ip_network(subnet.cidr_block)
        except ValueError:
            errors.append(f"Subnet {subnet.resource_id} has an invalid CIDR block.")
            continue
        if not network.subnet_of(vpc_network):
            errors.append(f"Subnet {subnet.resource_id} falls outside the VPC CIDR.")
        subnet_networks.append((subnet.resource_id, network))

    for index, (left_id, left_network) in enumerate(subnet_networks):
        for right_id, right_network in subnet_networks[index + 1 :]:
            if left_network.overlaps(right_network):
                errors.append(f"Subnets {left_id} and {right_id} overlap.")

    public_zones = {item.availability_zone for item in state.public_subnets}
    private_zones = {item.availability_zone for item in state.private_subnets}
    if len(public_zones) < 2:
        errors.append("Public subnets must span at least two Availability Zones.")
    if len(private_zones) < 2:
        errors.append("Private subnets must span at least two Availability Zones.")
    if public_zones != private_zones:
        errors.append("Each modeled Availability Zone needs public and private subnets.")

    associations: dict[str, str] = {}
    for table in state.route_tables:
        if table.vpc_id != state.vpc.resource_id:
            errors.append(f"Route table {table.resource_id} belongs to an unknown VPC.")
        for subnet_id in table.associated_subnet_ids:
            if subnet_id in associations:
                errors.append(f"Subnet {subnet_id} has multiple route-table associations.")
            associations[subnet_id] = table.resource_id

    for subnet in state.subnets:
        if associations.get(subnet.resource_id) != subnet.route_table_id:
            errors.append(
                f"Subnet {subnet.resource_id} route-table association is inconsistent."
            )
        table = next(
            (item for item in state.route_tables if item.resource_id == subnet.route_table_id),
            None,
        )
        if table is None:
            continue
        has_igw_default = any(
            route.destination_cidr == "0.0.0.0/0"
            and route.target_type == "internet_gateway"
            and route.target_id == state.internet_gateway.resource_id
            for route in table.routes
        )
        if subnet.subnet_type is SubnetType.PUBLIC and not has_igw_default:
            errors.append(f"Public subnet {subnet.resource_id} lacks an Internet route.")
        if subnet.subnet_type is SubnetType.PRIVATE and has_igw_default:
            errors.append(
                f"Private subnet {subnet.resource_id} must not route directly to the IGW."
            )
        if subnet.subnet_type is SubnetType.PRIVATE and subnet.assign_public_ip:
            errors.append(f"Private subnet {subnet.resource_id} assigns public IPs.")


def _validate_load_balancing(state: ArchitectureState, errors: list[str]) -> None:
    subnet_map = {item.resource_id: item for item in state.subnets}
    alb_subnets = [
        subnet_map[item]
        for item in state.load_balancer.subnet_ids
        if item in subnet_map
    ]
    if len(alb_subnets) != len(state.load_balancer.subnet_ids):
        errors.append("The load balancer references an unknown subnet.")
    if any(item.subnet_type is not SubnetType.PUBLIC for item in alb_subnets):
        errors.append("The internet-facing load balancer must use public subnets.")
    if len({item.availability_zone for item in alb_subnets}) < 2:
        errors.append("The load balancer must span at least two Availability Zones.")
    if state.load_balancer.scheme != "internet-facing":
        errors.append("The reference load balancer must be internet-facing.")
    if not state.load_balancer.cross_zone_enabled:
        errors.append("Cross-zone load balancing must remain enabled.")
    if state.load_balancer.target_group_id != state.target_group.resource_id:
        errors.append("The load balancer references an unknown target group.")
    if state.target_group.vpc_id != state.vpc.resource_id:
        errors.append("The target group belongs to an unknown VPC.")
    if state.target_group.health_check_path != "/health":
        errors.append("The target group health check must use /health.")
    if 200 not in state.target_group.healthy_status_codes:
        errors.append("The target group must accept HTTP 200 as healthy.")


def _validate_compute(state: ArchitectureState, errors: list[str]) -> None:
    group = state.auto_scaling_group
    if not (
        0 <= group.minimum_capacity <= group.desired_capacity <= group.maximum_capacity
    ):
        errors.append("Auto Scaling capacity must satisfy min <= desired <= max.")
    if group.health_check_type != "ELB":
        errors.append("The Auto Scaling Group must use ELB health checks.")
    if group.target_group_id != state.target_group.resource_id:
        errors.append("The Auto Scaling Group references an unknown target group.")

    subnet_map = {item.resource_id: item for item in state.subnets}
    if any(
        item not in subnet_map
        or subnet_map[item].subnet_type is not SubnetType.PRIVATE
        for item in group.subnet_ids
    ):
        errors.append("The Auto Scaling Group must use only private subnets.")
    group_zones = {
        subnet_map[item].availability_zone
        for item in group.subnet_ids
        if item in subnet_map
    }
    if len(group_zones) < 2:
        errors.append("The Auto Scaling Group must span at least two Availability Zones.")

    instance_ids = {item.resource_id for item in state.instances}
    if set(group.instance_ids) != instance_ids:
        errors.append("The Auto Scaling Group instance inventory is inconsistent.")
    if len(group.instance_ids) != group.desired_capacity:
        errors.append("Desired capacity must equal the initial instance count.")
    if set(state.target_group.registered_instance_ids) != instance_ids:
        errors.append("Every application instance must be registered in the target group.")

    security_group_ids = {item.resource_id for item in state.security_groups}
    for instance in state.instances:
        subnet = subnet_map.get(instance.subnet_id)
        if subnet is None:
            errors.append(f"Instance {instance.resource_id} references an unknown subnet.")
            continue
        if subnet.subnet_type is not SubnetType.PRIVATE:
            errors.append(f"Instance {instance.resource_id} must run in a private subnet.")
        if instance.availability_zone != subnet.availability_zone:
            errors.append(
                f"Instance {instance.resource_id} Availability Zone is inconsistent."
            )
        try:
            if ip_address(instance.private_ip) not in ip_network(subnet.cidr_block):
                errors.append(
                    f"Instance {instance.resource_id} private IP is outside its subnet."
                )
        except ValueError:
            errors.append(f"Instance {instance.resource_id} has an invalid private IP.")
        if instance.has_public_ip:
            errors.append(f"Instance {instance.resource_id} must not have a public IP.")
        if not set(instance.security_group_ids).issubset(security_group_ids):
            errors.append(
                f"Instance {instance.resource_id} references an unknown security group."
            )
        if instance.iam_role_id != state.iam_role.resource_id:
            errors.append(f"Instance {instance.resource_id} uses an unknown IAM role.")
        if instance.launch_template_id != group.launch_template_id:
            errors.append(
                f"Instance {instance.resource_id} does not use the ASG launch template."
            )


def _validate_security(state: ArchitectureState, errors: list[str]) -> None:
    group_map = {item.resource_id: item for item in state.security_groups}
    alb_group = group_map.get(state.load_balancer.security_group_id)
    if alb_group is None:
        errors.append("The load balancer references an unknown security group.")
        return

    app_group_ids = {
        group_id for instance in state.instances for group_id in instance.security_group_ids
    }
    app_groups = [group_map[item] for item in app_group_ids if item in group_map]
    if not any(
        "0.0.0.0/0" in rule.cidr_blocks
        and rule.protocol == "tcp"
        and rule.from_port <= state.load_balancer.listener_port <= rule.to_port
        for rule in alb_group.inbound_rules
    ):
        errors.append("The ALB security group must allow its public listener.")

    for group in app_groups:
        if any("0.0.0.0/0" in rule.cidr_blocks for rule in group.inbound_rules):
            errors.append("Application security groups must not allow public ingress.")
        if not any(
            rule.source_security_group_id == alb_group.resource_id
            and rule.protocol == "tcp"
            and rule.from_port <= state.target_group.port <= rule.to_port
            for rule in group.inbound_rules
        ):
            errors.append("Application ingress must be restricted to the ALB security group.")

    if state.iam_role.assumed_by_service != "ec2.amazonaws.com":
        errors.append("The application IAM role must be assumable only by EC2.")
    for statement in state.iam_role.policy_statements:
        if statement.effect != "Allow":
            errors.append("The reference IAM policy should contain reviewed Allow rules.")
        if "*" in statement.actions:
            errors.append("IAM actions must not contain a wildcard.")
        if "*" in statement.resources:
            errors.append("IAM resources must not contain a global wildcard.")
        if any(not action.startswith("s3:") for action in statement.actions):
            errors.append("The application role contains an unrelated IAM action.")


def _validate_storage_and_monitoring(
    state: ArchitectureState, errors: list[str]
) -> None:
    bucket = state.s3_bucket
    if not bucket.public_access_blocked:
        errors.append("The S3 bucket must block all public access.")
    if not bucket.encryption:
        errors.append("The S3 bucket must use server-side encryption.")
    if not bucket.versioning_enabled:
        errors.append("The S3 bucket must enable versioning.")
    if bucket.lifecycle_expiration_days <= 0:
        errors.append("The S3 lifecycle period must be positive.")

    if not state.cloudwatch.alarms:
        errors.append("At least one CloudWatch alarm is required.")
    alarm_ids = [item.resource_id for item in state.cloudwatch.alarms]
    if len(alarm_ids) != len(set(alarm_ids)):
        errors.append("CloudWatch alarm identifiers must be unique.")
    for alarm in state.cloudwatch.alarms:
        if alarm.evaluation_periods <= 0 or alarm.period_seconds <= 0:
            errors.append(f"Alarm {alarm.resource_id} has invalid evaluation settings.")
        metric_key = f"{alarm.namespace}:{alarm.metric_name}"
        if metric_key not in state.cloudwatch.tracked_metrics:
            errors.append(f"Alarm {alarm.resource_id} uses an untracked metric.")
