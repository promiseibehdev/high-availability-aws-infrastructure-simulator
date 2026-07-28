"""Typed, in-memory representations of the simulated AWS architecture."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class ResourceStatus(str, Enum):
    """Shared operational state for simulated infrastructure resources."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"


class SubnetType(str, Enum):
    """Network visibility of a subnet."""

    PUBLIC = "public"
    PRIVATE = "private"


class InstanceLifecycle(str, Enum):
    """Simplified EC2 lifecycle used by the simulation engine."""

    PENDING = "pending"
    IN_SERVICE = "in_service"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class HealthState(str, Enum):
    """Health-check state for instances and target registrations."""

    INITIAL = "initial"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class AlarmState(str, Enum):
    """CloudWatch-compatible alarm states used by the simulator."""

    OK = "OK"
    ALARM = "ALARM"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ComparisonOperator(str, Enum):
    """Supported threshold comparisons for simulated alarms."""

    GREATER_THAN_THRESHOLD = "GreaterThanThreshold"
    LESS_THAN_THRESHOLD = "LessThanThreshold"


@dataclass
class VPC:
    resource_id: str
    name: str
    cidr_block: str
    region: str
    dns_support: bool = True
    dns_hostnames: bool = True
    status: ResourceStatus = ResourceStatus.HEALTHY


@dataclass
class InternetGateway:
    resource_id: str
    name: str
    vpc_id: str
    status: ResourceStatus = ResourceStatus.HEALTHY


@dataclass(frozen=True)
class Route:
    destination_cidr: str
    target_type: str
    target_id: str


@dataclass
class RouteTable:
    resource_id: str
    name: str
    vpc_id: str
    routes: list[Route] = field(default_factory=list)
    associated_subnet_ids: list[str] = field(default_factory=list)
    status: ResourceStatus = ResourceStatus.HEALTHY


@dataclass
class Subnet:
    resource_id: str
    name: str
    vpc_id: str
    availability_zone: str
    cidr_block: str
    subnet_type: SubnetType
    route_table_id: str
    assign_public_ip: bool = False
    status: ResourceStatus = ResourceStatus.HEALTHY

    @property
    def is_public(self) -> bool:
        return self.subnet_type is SubnetType.PUBLIC


@dataclass(frozen=True)
class SecurityRule:
    description: str
    protocol: str
    from_port: int
    to_port: int
    cidr_blocks: tuple[str, ...] = ()
    source_security_group_id: str | None = None


@dataclass
class SecurityGroup:
    resource_id: str
    name: str
    description: str
    vpc_id: str
    inbound_rules: list[SecurityRule] = field(default_factory=list)
    outbound_rules: list[SecurityRule] = field(default_factory=list)


@dataclass(frozen=True)
class IAMPolicyStatement:
    effect: str
    actions: tuple[str, ...]
    resources: tuple[str, ...]


@dataclass
class IAMRole:
    resource_id: str
    name: str
    assumed_by_service: str
    policy_statements: list[IAMPolicyStatement] = field(default_factory=list)


@dataclass
class S3Bucket:
    resource_id: str
    name: str
    encryption: str
    public_access_blocked: bool
    versioning_enabled: bool
    lifecycle_expiration_days: int
    status: ResourceStatus = ResourceStatus.HEALTHY


@dataclass
class TargetGroup:
    resource_id: str
    name: str
    vpc_id: str
    protocol: str
    port: int
    health_check_path: str
    healthy_status_codes: tuple[int, ...]
    registered_instance_ids: list[str] = field(default_factory=list)
    status: ResourceStatus = ResourceStatus.HEALTHY


@dataclass
class ApplicationLoadBalancer:
    resource_id: str
    name: str
    scheme: str
    subnet_ids: list[str]
    security_group_id: str
    target_group_id: str
    listener_port: int
    listener_protocol: str
    cross_zone_enabled: bool = True
    status: ResourceStatus = ResourceStatus.HEALTHY


@dataclass
class AutoScalingGroup:
    resource_id: str
    name: str
    subnet_ids: list[str]
    launch_template_id: str
    target_group_id: str
    minimum_capacity: int
    desired_capacity: int
    maximum_capacity: int
    instance_ids: list[str] = field(default_factory=list)
    health_check_type: str = "ELB"
    status: ResourceStatus = ResourceStatus.HEALTHY


@dataclass
class EC2Instance:
    resource_id: str
    name: str
    subnet_id: str
    availability_zone: str
    private_ip: str
    security_group_ids: list[str]
    iam_role_id: str
    launch_template_id: str
    instance_type: str = "t3.micro"
    has_public_ip: bool = False
    lifecycle: InstanceLifecycle = InstanceLifecycle.IN_SERVICE
    health: HealthState = HealthState.HEALTHY
    cpu_utilization_percent: float = 18.0
    request_count: int = 0


@dataclass
class CloudWatchAlarm:
    resource_id: str
    name: str
    namespace: str
    metric_name: str
    comparison_operator: ComparisonOperator
    threshold: float
    evaluation_periods: int
    period_seconds: int
    dimensions: Mapping[str, str]
    state: AlarmState = AlarmState.OK
    description: str = ""


@dataclass
class CloudWatchResources:
    alarms: list[CloudWatchAlarm] = field(default_factory=list)
    tracked_metrics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchitectureNode:
    """Graphviz-ready node without a dependency on Graphviz itself."""

    node_id: str
    label: str
    resource_type: str
    group: str


@dataclass(frozen=True)
class ArchitectureEdge:
    """Directional relationship rendered by the future Graphviz layer."""

    source_id: str
    destination_id: str
    label: str


@dataclass
class ArchitectureState:
    """Complete internal state for one simulated AWS environment."""

    vpc: VPC
    internet_gateway: InternetGateway
    route_tables: list[RouteTable]
    subnets: list[Subnet]
    security_groups: list[SecurityGroup]
    iam_role: IAMRole
    s3_bucket: S3Bucket
    target_group: TargetGroup
    load_balancer: ApplicationLoadBalancer
    auto_scaling_group: AutoScalingGroup
    instances: list[EC2Instance]
    cloudwatch: CloudWatchResources

    def subnet(self, resource_id: str) -> Subnet:
        try:
            return next(item for item in self.subnets if item.resource_id == resource_id)
        except StopIteration as exc:
            raise KeyError(f"Unknown subnet resource: {resource_id}") from exc

    def instance(self, resource_id: str) -> EC2Instance:
        try:
            return next(
                item for item in self.instances if item.resource_id == resource_id
            )
        except StopIteration as exc:
            raise KeyError(f"Unknown EC2 instance resource: {resource_id}") from exc

    @property
    def public_subnets(self) -> list[Subnet]:
        return [item for item in self.subnets if item.subnet_type is SubnetType.PUBLIC]

    @property
    def private_subnets(self) -> list[Subnet]:
        return [item for item in self.subnets if item.subnet_type is SubnetType.PRIVATE]

    @property
    def healthy_instances(self) -> list[EC2Instance]:
        return [
            item
            for item in self.instances
            if item.lifecycle is InstanceLifecycle.IN_SERVICE
            and item.health is HealthState.HEALTHY
        ]
