"""Reference architecture factory and Graphviz-ready relationship model."""

from __future__ import annotations

from src.models import (
    VPC,
    ApplicationLoadBalancer,
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureState,
    AutoScalingGroup,
    CloudWatchAlarm,
    CloudWatchResources,
    ComparisonOperator,
    EC2Instance,
    IAMPolicyStatement,
    IAMRole,
    InternetGateway,
    Route,
    RouteTable,
    S3Bucket,
    SecurityGroup,
    SecurityRule,
    Subnet,
    SubnetType,
    TargetGroup,
)


def build_reference_architecture() -> ArchitectureState:
    """Create a production-shaped, entirely local two-AZ architecture state."""

    vpc = VPC(
        resource_id="vpc-main",
        name="simulated-production-vpc",
        cidr_block="10.20.0.0/16",
        region="us-east-1",
    )
    internet_gateway = InternetGateway(
        resource_id="igw-main",
        name="simulated-internet-gateway",
        vpc_id=vpc.resource_id,
    )
    public_route_table = RouteTable(
        resource_id="rtb-public",
        name="public-route-table",
        vpc_id=vpc.resource_id,
        routes=[
            Route("10.20.0.0/16", "local", vpc.resource_id),
            Route("0.0.0.0/0", "internet_gateway", internet_gateway.resource_id),
        ],
        associated_subnet_ids=["subnet-public-a", "subnet-public-b"],
    )
    private_route_table_a = RouteTable(
        resource_id="rtb-private-a",
        name="private-route-table-a",
        vpc_id=vpc.resource_id,
        routes=[Route("10.20.0.0/16", "local", vpc.resource_id)],
        associated_subnet_ids=["subnet-private-a"],
    )
    private_route_table_b = RouteTable(
        resource_id="rtb-private-b",
        name="private-route-table-b",
        vpc_id=vpc.resource_id,
        routes=[Route("10.20.0.0/16", "local", vpc.resource_id)],
        associated_subnet_ids=["subnet-private-b"],
    )
    subnets = [
        Subnet(
            "subnet-public-a",
            "public-subnet-a",
            vpc.resource_id,
            "us-east-1a",
            "10.20.0.0/24",
            SubnetType.PUBLIC,
            public_route_table.resource_id,
            assign_public_ip=True,
        ),
        Subnet(
            "subnet-public-b",
            "public-subnet-b",
            vpc.resource_id,
            "us-east-1b",
            "10.20.1.0/24",
            SubnetType.PUBLIC,
            public_route_table.resource_id,
            assign_public_ip=True,
        ),
        Subnet(
            "subnet-private-a",
            "private-subnet-a",
            vpc.resource_id,
            "us-east-1a",
            "10.20.10.0/24",
            SubnetType.PRIVATE,
            private_route_table_a.resource_id,
        ),
        Subnet(
            "subnet-private-b",
            "private-subnet-b",
            vpc.resource_id,
            "us-east-1b",
            "10.20.11.0/24",
            SubnetType.PRIVATE,
            private_route_table_b.resource_id,
        ),
    ]
    alb_security_group = SecurityGroup(
        resource_id="sg-alb",
        name="alb-security-group",
        description="Allows public HTTP traffic to the simulated ALB.",
        vpc_id=vpc.resource_id,
        inbound_rules=[
            SecurityRule("Public HTTP", "tcp", 80, 80, ("0.0.0.0/0",)),
        ],
        outbound_rules=[
            SecurityRule(
                "Application traffic",
                "tcp",
                8080,
                8080,
                source_security_group_id="sg-app",
            )
        ],
    )
    app_security_group = SecurityGroup(
        resource_id="sg-app",
        name="application-security-group",
        description="Accepts application traffic only from the ALB.",
        vpc_id=vpc.resource_id,
        inbound_rules=[
            SecurityRule(
                "Traffic from ALB",
                "tcp",
                8080,
                8080,
                source_security_group_id=alb_security_group.resource_id,
            )
        ],
        outbound_rules=[],
    )
    s3_bucket = S3Bucket(
        resource_id="s3-artifacts",
        name="simulated-private-artifacts",
        encryption="AES256",
        public_access_blocked=True,
        versioning_enabled=True,
        lifecycle_expiration_days=30,
    )
    iam_role = IAMRole(
        resource_id="iam-app-role",
        name="simulated-ec2-application-role",
        assumed_by_service="ec2.amazonaws.com",
        policy_statements=[
            IAMPolicyStatement(
                effect="Allow",
                actions=("s3:GetObject",),
                resources=(
                    "arn:aws:s3:::simulated-private-artifacts/application/*",
                ),
            )
        ],
    )
    instances = [
        EC2Instance(
            resource_id="i-app-a",
            name="application-instance-a",
            subnet_id="subnet-private-a",
            availability_zone="us-east-1a",
            private_ip="10.20.10.10",
            security_group_ids=[app_security_group.resource_id],
            iam_role_id=iam_role.resource_id,
            launch_template_id="lt-app-v1",
        ),
        EC2Instance(
            resource_id="i-app-b",
            name="application-instance-b",
            subnet_id="subnet-private-b",
            availability_zone="us-east-1b",
            private_ip="10.20.11.10",
            security_group_ids=[app_security_group.resource_id],
            iam_role_id=iam_role.resource_id,
            launch_template_id="lt-app-v1",
            cpu_utilization_percent=22.0,
        ),
    ]
    target_group = TargetGroup(
        resource_id="tg-app",
        name="application-target-group",
        vpc_id=vpc.resource_id,
        protocol="HTTP",
        port=8080,
        health_check_path="/health",
        healthy_status_codes=(200,),
        registered_instance_ids=[item.resource_id for item in instances],
    )
    load_balancer = ApplicationLoadBalancer(
        resource_id="alb-public",
        name="public-application-load-balancer",
        scheme="internet-facing",
        subnet_ids=["subnet-public-a", "subnet-public-b"],
        security_group_id=alb_security_group.resource_id,
        target_group_id=target_group.resource_id,
        listener_port=80,
        listener_protocol="HTTP",
    )
    auto_scaling_group = AutoScalingGroup(
        resource_id="asg-app",
        name="application-auto-scaling-group",
        subnet_ids=["subnet-private-a", "subnet-private-b"],
        launch_template_id="lt-app-v1",
        target_group_id=target_group.resource_id,
        minimum_capacity=2,
        desired_capacity=2,
        maximum_capacity=4,
        instance_ids=[item.resource_id for item in instances],
    )
    cloudwatch = CloudWatchResources(
        tracked_metrics=(
            "AWS/EC2:CPUUtilization",
            "AWS/ApplicationELB:HealthyHostCount",
            "AWS/ApplicationELB:UnHealthyHostCount",
            "AWS/ApplicationELB:HTTPCode_ELB_5XX_Count",
            "AWS/AutoScaling:GroupInServiceInstances",
        ),
        alarms=[
            CloudWatchAlarm(
                resource_id="alarm-high-cpu",
                name="high-cpu-utilization",
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
                threshold=70.0,
                evaluation_periods=2,
                period_seconds=60,
                dimensions={"AutoScalingGroupName": auto_scaling_group.name},
                description="Signals that the application tier may need to scale out.",
            ),
            CloudWatchAlarm(
                resource_id="alarm-unhealthy-hosts",
                name="unhealthy-targets",
                namespace="AWS/ApplicationELB",
                metric_name="UnHealthyHostCount",
                comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
                threshold=0.0,
                evaluation_periods=1,
                period_seconds=60,
                dimensions={"TargetGroup": target_group.name},
                description="Signals that at least one target is unhealthy.",
            ),
            CloudWatchAlarm(
                resource_id="alarm-low-capacity",
                name="insufficient-in-service-capacity",
                namespace="AWS/AutoScaling",
                metric_name="GroupInServiceInstances",
                comparison_operator=ComparisonOperator.LESS_THAN_THRESHOLD,
                threshold=2.0,
                evaluation_periods=1,
                period_seconds=60,
                dimensions={"AutoScalingGroupName": auto_scaling_group.name},
                description="Signals loss of the desired highly available capacity.",
            ),
        ],
    )
    return ArchitectureState(
        vpc=vpc,
        internet_gateway=internet_gateway,
        route_tables=[
            public_route_table,
            private_route_table_a,
            private_route_table_b,
        ],
        subnets=subnets,
        security_groups=[alb_security_group, app_security_group],
        iam_role=iam_role,
        s3_bucket=s3_bucket,
        target_group=target_group,
        load_balancer=load_balancer,
        auto_scaling_group=auto_scaling_group,
        instances=instances,
        cloudwatch=cloudwatch,
    )


def build_graph_spec(
    state: ArchitectureState,
) -> tuple[list[ArchitectureNode], list[ArchitectureEdge]]:
    """Translate state into neutral nodes and edges for future Graphviz rendering."""

    nodes = [
        ArchitectureNode(state.vpc.resource_id, state.vpc.name, "VPC", "network"),
        ArchitectureNode(
            state.internet_gateway.resource_id,
            state.internet_gateway.name,
            "Internet Gateway",
            "network",
        ),
        ArchitectureNode(
            state.load_balancer.resource_id,
            state.load_balancer.name,
            "Application Load Balancer",
            "load-balancing",
        ),
        ArchitectureNode(
            state.target_group.resource_id,
            state.target_group.name,
            "Target Group",
            "load-balancing",
        ),
        ArchitectureNode(
            state.auto_scaling_group.resource_id,
            state.auto_scaling_group.name,
            "Auto Scaling Group",
            "compute",
        ),
        ArchitectureNode(
            state.iam_role.resource_id,
            state.iam_role.name,
            "IAM Role",
            "security",
        ),
        ArchitectureNode(
            state.s3_bucket.resource_id,
            state.s3_bucket.name,
            "S3 Bucket",
            "storage",
        ),
    ]
    nodes.extend(
        ArchitectureNode(item.resource_id, item.name, "Subnet", item.subnet_type.value)
        for item in state.subnets
    )
    nodes.extend(
        ArchitectureNode(item.resource_id, item.name, "Route Table", "network")
        for item in state.route_tables
    )
    nodes.extend(
        ArchitectureNode(item.resource_id, item.name, "Security Group", "security")
        for item in state.security_groups
    )
    nodes.extend(
        ArchitectureNode(item.resource_id, item.name, "EC2 Instance", "compute")
        for item in state.instances
    )
    nodes.extend(
        ArchitectureNode(item.resource_id, item.name, "CloudWatch Alarm", "monitoring")
        for item in state.cloudwatch.alarms
    )

    edges = [
        ArchitectureEdge(
            state.internet_gateway.resource_id, state.vpc.resource_id, "attached to"
        ),
        ArchitectureEdge(
            state.load_balancer.resource_id,
            state.target_group.resource_id,
            "forwards to",
        ),
        ArchitectureEdge(
            state.auto_scaling_group.resource_id,
            state.target_group.resource_id,
            "registers targets",
        ),
        ArchitectureEdge(
            state.iam_role.resource_id, state.s3_bucket.resource_id, "reads artifacts"
        ),
    ]
    edges.extend(
        ArchitectureEdge(state.vpc.resource_id, subnet.resource_id, "contains")
        for subnet in state.subnets
    )
    edges.extend(
        ArchitectureEdge(instance.subnet_id, instance.resource_id, "hosts")
        for instance in state.instances
    )
    edges.extend(
        ArchitectureEdge(
            state.target_group.resource_id, instance_id, "health checks"
        )
        for instance_id in state.target_group.registered_instance_ids
    )
    return nodes, edges
