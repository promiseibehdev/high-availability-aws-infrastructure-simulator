"""Static Terraform learning content for the fully offline explorer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TerraformExample:
    component_id: str
    name: str
    resource_types: tuple[str, ...]
    explanation: str
    important_arguments: tuple[str, ...]
    dependencies: tuple[str, ...]
    security_considerations: tuple[str, ...]
    best_practices: tuple[str, ...]
    hcl: str


@dataclass(frozen=True)
class LifecycleStep:
    command: str
    purpose: str
    educational_output: str
    changes_infrastructure: bool


def _example(
    component_id: str,
    name: str,
    resource_types: tuple[str, ...],
    explanation: str,
    arguments: tuple[str, ...],
    dependencies: tuple[str, ...],
    security: tuple[str, ...],
    practices: tuple[str, ...],
    hcl: str,
) -> TerraformExample:
    return TerraformExample(
        component_id,
        name,
        resource_types,
        explanation,
        arguments,
        dependencies,
        security,
        practices,
        hcl.strip(),
    )


TERRAFORM_EXAMPLES = (
    _example(
        "vpc",
        "VPC",
        ("VPC",),
        "Creates the isolated regional network boundary used by every other resource.",
        ("cidr_block", "enable_dns_support", "enable_dns_hostnames", "tags"),
        ("AWS provider configuration",),
        ("Use a non-overlapping private CIDR.", "Keep DNS enabled for AWS service discovery."),
        ("Plan address growth before choosing the CIDR.", "Apply consistent ownership tags."),
        """
resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "production-vpc" }
}
""",
    ),
    _example(
        "internet-gateway",
        "Internet Gateway",
        ("Internet Gateway",),
        "Attaches internet routing capability to the VPC for public subnet resources.",
        ("vpc_id", "tags"),
        ("aws_vpc.main",),
        ("An attachment alone exposes nothing; routes and resource addressing matter.",),
        ("Route only public subnets to the gateway.",),
        """
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "production-igw" }
}
""",
    ),
    _example(
        "route-tables",
        "Route Tables",
        ("Route Table",),
        "Separates public internet routing from private application routing.",
        ("vpc_id", "route", "gateway_id", "subnet_id"),
        ("aws_vpc.main", "aws_internet_gateway.main", "aws_subnet.public"),
        ("Never add a direct Internet Gateway default route to private subnets.",),
        ("Use explicit subnet associations.", "Use one private route table per AZ when NAT is required."),
        """
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}
""",
    ),
    _example(
        "public-subnets",
        "Public Subnets",
        ("Public Subnet",),
        "Places the internet-facing ALB across two Availability Zones.",
        ("for_each", "vpc_id", "cidr_block", "availability_zone"),
        ("aws_vpc.main", "public route table associations"),
        ("Reserve public subnets for resources that truly require public routing.",),
        ("Use at least two AZs.", "Calculate CIDRs deterministically."),
        """
resource "aws_subnet" "public" {
  for_each = {
    a = { az = "us-east-1a", cidr = "10.20.0.0/24" }
    b = { az = "us-east-1b", cidr = "10.20.1.0/24" }
  }

  vpc_id                  = aws_vpc.main.id
  availability_zone       = each.value.az
  cidr_block              = each.value.cidr
  map_public_ip_on_launch = false
}
""",
    ),
    _example(
        "private-subnets",
        "Private Subnets",
        ("Private Subnet",),
        "Hosts application compute without a direct route from the internet.",
        ("for_each", "vpc_id", "cidr_block", "availability_zone"),
        ("aws_vpc.main", "private route table associations"),
        ("Do not assign public IPv4 addresses or route directly to an IGW.",),
        ("Spread compute across AZs.", "Add controlled egress only when required."),
        """
resource "aws_subnet" "private" {
  for_each = {
    a = { az = "us-east-1a", cidr = "10.20.10.0/24" }
    b = { az = "us-east-1b", cidr = "10.20.11.0/24" }
  }

  vpc_id                  = aws_vpc.main.id
  availability_zone       = each.value.az
  cidr_block              = each.value.cidr
  map_public_ip_on_launch = false
}
""",
    ),
    _example(
        "security-groups",
        "Security Groups",
        ("Security Group",),
        "Creates a narrow trust chain from public clients to the ALB and then to the app.",
        ("security_group_id", "referenced_security_group_id", "from_port", "to_port"),
        ("aws_vpc.main",),
        ("Never expose SSH.", "Reference the ALB group instead of a public CIDR for app ingress."),
        ("Use separate rule resources.", "Describe the reason for every rule."),
        """
resource "aws_security_group" "alb" {
  name   = "alb-sg"
  vpc_id = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
}
""",
    ),
    _example(
        "alb",
        "Application Load Balancer",
        ("Application Load Balancer",),
        "Provides the managed public entry point across both public subnets.",
        ("internal", "load_balancer_type", "subnets", "security_groups"),
        ("public subnets", "ALB security group"),
        ("Terminate HTTPS in production.", "Allow only required listener ports."),
        ("Deploy in at least two AZs.", "Enable access logs when operationally useful."),
        """
resource "aws_lb" "app" {
  name               = "production-app-alb"
  internal           = false
  load_balancer_type = "application"
  subnets             = values(aws_subnet.public)[*].id
  security_groups     = [aws_security_group.alb.id]
}
""",
    ),
    _example(
        "target-group",
        "Target Group",
        ("Target Group",),
        "Defines application routing and health-check behavior for Auto Scaling targets.",
        ("port", "protocol", "vpc_id", "health_check"),
        ("aws_vpc.main", "aws_lb.app", "Auto Scaling Group"),
        ("Use an application-aware health endpoint that reveals readiness.",),
        ("Tune thresholds to startup time.", "Use a safe deregistration delay."),
        """
resource "aws_lb_target_group" "app" {
  name     = "production-app"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path    = "/health"
    matcher = "200"
  }
}
""",
    ),
    _example(
        "auto-scaling-group",
        "Auto Scaling Group",
        ("Auto Scaling Group",),
        "Maintains healthy multi-AZ capacity and replaces failed instances.",
        ("min_size", "desired_capacity", "max_size", "vpc_zone_identifier"),
        ("launch template", "private subnets", "target group"),
        ("Keep instances private and use ELB health checks.",),
        ("Use lifecycle hooks for graceful shutdown.", "Protect minimum multi-AZ capacity."),
        """
resource "aws_autoscaling_group" "app" {
  min_size            = 2
  desired_capacity    = 2
  max_size            = 4
  vpc_zone_identifier = values(aws_subnet.private)[*].id
  target_group_arns   = [aws_lb_target_group.app.arn]
  health_check_type   = "ELB"

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}
""",
    ),
    _example(
        "launch-template",
        "Launch Template",
        ("Launch Template",),
        "Defines the repeatable, hardened EC2 configuration used by Auto Scaling.",
        ("image_id", "instance_type", "iam_instance_profile", "metadata_options"),
        ("app security group", "IAM instance profile"),
        ("Require IMDSv2.", "Encrypt EBS.", "Do not assign public IPs."),
        ("Pin a reviewed AMI.", "Use versioned templates for safe rollouts."),
        """
resource "aws_launch_template" "app" {
  name_prefix   = "production-app-"
  image_id      = var.ami_id
  instance_type = "t3.micro"

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs { encrypted = true }
  }
}
""",
    ),
    _example(
        "ec2",
        "EC2 Instances",
        ("EC2 Instance",),
        "Represents application servers created indirectly and replaced by Auto Scaling.",
        ("launch_template", "subnet placement", "desired_capacity"),
        ("aws_launch_template.app", "aws_autoscaling_group.app"),
        ("No public IP or inbound SSH.", "Use role credentials instead of access keys."),
        ("Treat instances as disposable.", "Do not manage ASG instances with aws_instance resources."),
        """
# Production instances are created by the Auto Scaling Group.
# Do not also declare aws_instance resources for the same fleet.
launch_template {
  id      = aws_launch_template.app.id
  version = "$Latest"
}
""",
    ),
    _example(
        "iam",
        "IAM Role",
        ("IAM Role",),
        "Gives EC2 temporary, narrowly scoped access to one S3 object prefix.",
        ("assume_role_policy", "policy actions", "resource ARN", "instance profile"),
        ("S3 bucket", "launch template"),
        ("Avoid wildcard actions and resources.", "Never store access keys in Terraform."),
        ("Separate trust and permission policies.", "Use jsonencode for valid JSON."),
        """
resource "aws_iam_role" "app" {
  name = "production-app-role"
  assume_role_policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "read_artifacts" {
  role = aws_iam_role.app.id
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "${aws_s3_bucket.artifacts.arn}/application/*"
    }]
  })
}
""",
    ),
    _example(
        "s3",
        "S3 Bucket",
        ("S3 Bucket",),
        "Stores private application artifacts with encryption, versioning, and public blocking.",
        ("bucket", "server_side_encryption_configuration", "versioning", "public_access_block"),
        ("IAM role policy",),
        ("Block all public access.", "Encrypt objects and restrict principals."),
        ("Use a generated globally unique name.", "Add lifecycle and retention intentionally."),
        """
resource "aws_s3_bucket" "artifacts" {
  bucket = var.artifact_bucket_name
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}
""",
    ),
    _example(
        "cloudwatch",
        "CloudWatch",
        ("CloudWatch Alarm",),
        "Defines actionable alarms for load, unhealthy targets, and insufficient capacity.",
        ("namespace", "metric_name", "threshold", "evaluation_periods", "dimensions"),
        ("Auto Scaling Group", "target group"),
        ("Do not place secrets in logs.", "Route notifications only to approved destinations."),
        ("Document missing-data behavior.", "Alarm on actionable symptoms."),
        """
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "production-high-cpu"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 70
  evaluation_periods  = 2
  period              = 60
  statistic           = "Average"
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.app.name
  }
}
""",
    ),
)


TERRAFORM_EXAMPLE_BY_ID = {item.component_id: item for item in TERRAFORM_EXAMPLES}

RESOURCE_TYPE_TO_COMPONENT = {
    resource_type: item.component_id
    for item in TERRAFORM_EXAMPLES
    for resource_type in item.resource_types
}


def component_for_resource(resource_id: str, resource_type: str) -> str:
    """Map a selected simulator resource to its closest Terraform component."""

    if resource_id.startswith("subnet-public"):
        return "public-subnets"
    if resource_id.startswith("subnet-private"):
        return "private-subnets"
    if resource_id.startswith("alarm-"):
        return "cloudwatch"
    if resource_id.startswith("i-"):
        return "ec2"
    return RESOURCE_TYPE_TO_COMPONENT.get(resource_type, "vpc")


TERRAFORM_LIFECYCLE = (
    LifecycleStep(
        "terraform init",
        "Downloads providers and initializes backend metadata.",
        "Demo output: initialization would complete successfully.",
        False,
    ),
    LifecycleStep(
        "terraform validate",
        "Checks syntax and internal configuration consistency.",
        "Demo output: configuration is valid.",
        False,
    ),
    LifecycleStep(
        "terraform fmt -check",
        "Checks canonical HCL formatting without changing files.",
        "Demo output: all example files are consistently formatted.",
        False,
    ),
    LifecycleStep(
        "terraform plan",
        "Previews the proposed resource changes.",
        "Demo output: a production plan would show resources to add, change, or destroy.",
        False,
    ),
    LifecycleStep(
        "terraform apply",
        "Creates or changes infrastructure after plan review and approval.",
        "Demo only: not executed because it could create chargeable AWS resources.",
        True,
    ),
    LifecycleStep(
        "terraform destroy",
        "Plans and removes resources managed by the selected state.",
        "Demo only: not executed; production teams review a destroy plan first.",
        True,
    ),
)


VALIDATION_GUIDES = (
    (
        "terraform fmt",
        "Canonical formatting makes reviews smaller and HCL easier to scan.",
        "Educational result: formatting check passed.",
    ),
    (
        "terraform validate",
        "Finds syntax, type, and internal reference problems without planning AWS changes.",
        "Educational result: configuration is internally valid.",
    ),
    (
        "TFLint",
        "Adds Terraform and provider-aware lint rules, including deprecated arguments and conventions.",
        "Educational result: no lint findings shown in this static demonstration.",
    ),
    (
        "Checkov / Trivy",
        "Static security scanners flag risky IaC patterns such as public storage or open SSH.",
        "Educational result: security examples are illustrative, not a completed compliance audit.",
    ),
)


PRODUCTION_DEMO_COMPARISON = (
    ("Purpose", "Runs a real workload", "Teaches architecture behavior safely"),
    ("Infrastructure", "Creates AWS resources", "Uses immutable Python simulation state"),
    ("Credentials", "Requires controlled AWS authentication", "Requires no credentials"),
    ("Terraform", "Reviewed plan is applied by an authorized workflow", "HCL is display-only"),
    ("Observability", "CloudWatch receives real telemetry", "Metrics are deterministic examples"),
    ("Cost", "ALB, NAT, EC2, storage, IP, and transfer may charge", "$0 in AWS charges"),
    ("Availability", "AWS services span multiple AZs", "Failure behavior is replayed locally"),
)
