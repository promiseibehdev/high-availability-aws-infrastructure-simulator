"""Reviewed educational explanations for architecture and security concepts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentGuide:
    component_id: str
    name: str
    what_it_is: str
    why_it_exists: str
    best_practices: tuple[str, ...]
    interview_tip: str


@dataclass(frozen=True)
class SecurityControl:
    control_id: str
    name: str
    implementation: str
    reason: str
    evidence: str


@dataclass(frozen=True)
class MisconfigurationExample:
    name: str
    risk: str
    safer_design: str


COMPONENT_GUIDES = (
    ComponentGuide(
        "vpc",
        "Virtual Private Cloud",
        "A logically isolated network boundary inside an AWS Region.",
        "It gives the application controlled address space, routing, and security boundaries.",
        (
            "Choose non-overlapping CIDR ranges.",
            "Separate public entry points from private workloads.",
            "Enable DNS support and document traffic flows.",
        ),
        "Explain that a public subnet is public because of its route table, not its name.",
    ),
    ComponentGuide(
        "internet-gateway",
        "Internet Gateway",
        "A horizontally scaled VPC component that connects public routes to the internet.",
        "The internet-facing ALB needs a route through it to receive user traffic.",
        (
            "Attach only one Internet Gateway to the VPC.",
            "Route only intended public subnets to it.",
            "Do not give private application instances direct IGW routes.",
        ),
        "Contrast an Internet Gateway with a NAT Gateway: inbound public access versus outbound-only translation.",
    ),
    ComponentGuide(
        "route-tables",
        "Route Tables",
        "Rules that decide where subnet traffic is sent.",
        "They create the actual distinction between public and private network paths.",
        (
            "Use explicit subnet associations.",
            "Keep private route tables separate by Availability Zone in production.",
            "Review default routes carefully.",
        ),
        "A subnet with a 0.0.0.0/0 route to an IGW is public only when resources can also use public addresses.",
    ),
    ComponentGuide(
        "public-subnets",
        "Public Subnets",
        "Subnets whose route table can reach an Internet Gateway.",
        "They host the public ALB nodes while keeping application servers private.",
        (
            "Place only resources that require public routing here.",
            "Use at least two Availability Zones.",
            "Apply narrow security-group ingress.",
        ),
        "Public subnets do not mean every resource inside them should accept public traffic.",
    ),
    ComponentGuide(
        "private-subnets",
        "Private Subnets",
        "Subnets without a direct route from the internet.",
        "They reduce the attack surface of EC2 application servers.",
        (
            "Do not assign public IP addresses.",
            "Allow application ingress only from the ALB security group.",
            "Use controlled egress only when workloads need it.",
        ),
        "Describe private subnets as a defense-in-depth boundary, not a replacement for security groups.",
    ),
    ComponentGuide(
        "alb",
        "Application Load Balancer",
        "A Layer 7 load balancer for HTTP and HTTPS applications.",
        "It distributes requests, performs health checks, and isolates clients from EC2 instances.",
        (
            "Deploy across at least two Availability Zones.",
            "Use HTTPS and managed certificates in production.",
            "Configure meaningful health paths and deregistration delay.",
        ),
        "Mention host/path routing, health checks, and cross-zone distribution.",
    ),
    ComponentGuide(
        "target-group",
        "Target Group",
        "A collection of application endpoints registered behind a load balancer.",
        "It connects ALB routing and health checks to Auto Scaling instances.",
        (
            "Use an application-aware /health endpoint.",
            "Set a realistic healthy status-code matcher.",
            "Align health-check grace periods with startup time.",
        ),
        "ALB health and EC2 system health answer different questions; production designs often use both.",
    ),
    ComponentGuide(
        "asg",
        "Auto Scaling Group",
        "A controller that maintains and adjusts a fleet of EC2 instances.",
        "It replaces unhealthy instances and spreads capacity across Availability Zones.",
        (
            "Set minimum healthy multi-AZ capacity.",
            "Use ELB health checks for application-aware replacement.",
            "Use cooldowns and conservative scale-in policies.",
        ),
        "High availability comes from redundancy plus automated replacement, not scaling alone.",
    ),
    ComponentGuide(
        "ec2",
        "EC2 Application Instances",
        "Virtual machines that run the application workload.",
        "They provide replaceable compute targets behind the ALB.",
        (
            "Treat instances as disposable.",
            "Require IMDSv2 and encrypted EBS.",
            "Avoid public IPs and inbound SSH.",
        ),
        "Immutable launch templates make replacement and rollback more reliable.",
    ),
    ComponentGuide(
        "security-groups",
        "Security Groups",
        "Stateful virtual firewalls attached to AWS resources.",
        "They permit only the intended ALB-to-application traffic path.",
        (
            "Reference security groups instead of broad CIDRs internally.",
            "Avoid 0.0.0.0/0 on administrative ports.",
            "Review both ingress and egress.",
        ),
        "Security groups are stateful; network ACLs are stateless subnet controls.",
    ),
    ComponentGuide(
        "iam",
        "Least-Privilege IAM Role",
        "Temporary AWS permissions assumed by an EC2 workload.",
        "It avoids embedded access keys while allowing one required S3 read operation.",
        (
            "Scope actions and resources.",
            "Use roles instead of long-lived credentials.",
            "Review trust and permission policies separately.",
        ),
        "Least privilege means granting the smallest useful action on the smallest useful resource.",
    ),
    ComponentGuide(
        "s3",
        "Private S3 Bucket",
        "Durable object storage for artifacts or logs.",
        "It demonstrates encrypted, versioned storage that is not publicly readable.",
        (
            "Block all public access.",
            "Enable encryption and versioning.",
            "Use lifecycle policies and resource-scoped IAM.",
        ),
        "S3 bucket policies, IAM policies, access points, and public-access blocks work together.",
    ),
    ComponentGuide(
        "cloudwatch",
        "CloudWatch Monitoring",
        "AWS metrics, alarms, logs, and observability services.",
        "It makes failures visible and can trigger operational notifications or scaling.",
        (
            "Alarm on symptoms users experience and capacity risks.",
            "Use actionable thresholds.",
            "Document missing-data behavior and recovery actions.",
        ),
        "An alarm is useful only when it has an owner, an action, and enough context to investigate.",
    ),
)


SECURITY_CONTROLS = (
    SecurityControl(
        "vpc-isolation",
        "VPC isolation",
        "All simulated resources live inside one documented 10.20.0.0/16 boundary.",
        "A dedicated network boundary makes routing and access paths explicit.",
        "One VPC contains four non-overlapping subnets.",
    ),
    SecurityControl(
        "subnet-separation",
        "Public and private subnet separation",
        "Only the ALB occupies public subnets; application instances occupy private subnets.",
        "Internet entry points and application compute have different exposure requirements.",
        "Two public and two private subnets span both zones.",
    ),
    SecurityControl(
        "security-groups",
        "Security-group chaining",
        "The application security group accepts port 8080 only from the ALB security group.",
        "Referencing the ALB group is narrower and more maintainable than public CIDRs.",
        "No application rule permits 0.0.0.0/0.",
    ),
    SecurityControl(
        "least-privilege",
        "Least-privilege IAM role",
        "EC2 receives only s3:GetObject for one application prefix.",
        "Workloads should receive only the permissions needed for their function.",
        "No wildcard action or global resource is present.",
    ),
    SecurityControl(
        "private-compute",
        "Private EC2 instances",
        "Application instances have private addresses and no public IPv4 addresses.",
        "Direct public reachability is unnecessary behind an ALB.",
        "Both instances are modeled in private subnets.",
    ),
    SecurityControl(
        "alb-ingress",
        "ALB-only ingress",
        "Users reach the ALB; the ALB security group is the application's only source.",
        "A single controlled entry point reduces exposed surface area.",
        "Target port 8080 is never opened directly to the internet.",
    ),
    SecurityControl(
        "s3-encryption",
        "Encrypted private S3",
        "The bucket blocks public access, enables AES256 encryption and uses versioning.",
        "Stored artifacts need confidentiality and recoverability.",
        "The architecture validator rejects public or unencrypted storage.",
    ),
    SecurityControl(
        "imdsv2",
        "IMDSv2 requirement",
        "The production launch-template design requires session-oriented instance metadata.",
        "IMDSv2 reduces exposure to metadata-request abuse such as basic SSRF paths.",
        "Represented as a documented launch-template invariant.",
    ),
    SecurityControl(
        "no-ssh",
        "No public SSH",
        "No security group exposes TCP port 22 and no public instance address is assigned.",
        "Routine administration should not require an internet-facing management port.",
        "The simulated inbound rules expose only ALB HTTP and internal application traffic.",
    ),
    SecurityControl(
        "encryption-at-rest",
        "Encryption at rest",
        "S3 and the production EBS design use encryption at rest.",
        "Encryption limits exposure if stored media or snapshots are accessed improperly.",
        "S3 encryption is modeled now; encrypted EBS is an explicit launch-template best practice.",
    ),
)


MISCONFIGURATIONS = (
    MisconfigurationExample(
        "Public SSH from anywhere",
        "TCP 22 from 0.0.0.0/0 invites password attacks and increases administrative exposure.",
        "Use no public SSH; prefer controlled systems-management access in a real environment.",
    ),
    MisconfigurationExample(
        "Public EC2 application servers",
        "Public addresses bypass the intended ALB inspection and health-routing path.",
        "Place EC2 in private subnets and allow application ingress only from the ALB group.",
    ),
    MisconfigurationExample(
        "Wildcard IAM permissions",
        "Broad actions or resources can turn one application compromise into account-wide impact.",
        "Scope the action, bucket and object prefix to the workload's exact requirement.",
    ),
    MisconfigurationExample(
        "Public or unencrypted S3",
        "Artifacts may be exposed, modified, or read outside the intended application path.",
        "Block public access, encrypt objects, enable versioning and restrict IAM.",
    ),
    MisconfigurationExample(
        "Private subnet routed directly to an IGW",
        "The route undermines the intended isolation boundary when public addresses are present.",
        "Keep direct IGW routes in public route tables only.",
    ),
)
