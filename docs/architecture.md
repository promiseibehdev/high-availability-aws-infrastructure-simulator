# Architecture Guide

## Purpose

The reference design represents a highly available web application on AWS. It is
production-shaped rather than production-deployed: the simulator models the
resources and their behavior entirely in Python.

This distinction is important. The design teaches real architectural relationships,
but opening the application never creates a VPC, load balancer, EC2 instance, S3
bucket, alarm, or AWS bill.

## Request Flow

```text
User
  → Internet Gateway
  → Internet-facing Application Load Balancer
  → Target Group health and routing decision
  → Healthy EC2 application instance in a private subnet
  → Least-privilege IAM access to private S3 objects, when required
```

CloudWatch-style metrics and alarms observe the simulated application path. The
Auto Scaling Group maintains the desired number of instances and replaces unhealthy
capacity.

## Regional and VPC Boundary

The model uses one VPC in `us-east-1` with CIDR `10.20.0.0/16`. DNS support and DNS
hostnames are enabled in the resource model.

A VPC provides an isolated address and routing boundary. The CIDR is deliberately
larger than the four modeled `/24` subnets so a real design could add workload,
database, endpoint, or management subnets without renumbering immediately.

## Two-Availability-Zone Layout

| Availability Zone | Public subnet | Private subnet |
|---|---|---|
| `us-east-1a` | `10.20.0.0/24` | `10.20.10.0/24` |
| `us-east-1b` | `10.20.1.0/24` | `10.20.11.0/24` |

Using two zones prevents one simulated zone failure from removing all application
capacity. Each zone has a public subnet for an ALB node and a private subnet for
application compute.

## Public and Private Routing

The public route table has a default route to the Internet Gateway. Both public
subnets associate with this table.

Private route tables contain only the local VPC route in the simulator. They have no
direct Internet Gateway route, which reinforces that private EC2 instances should
not be directly internet-accessible.

A real application may require controlled outbound access through NAT Gateways or
VPC endpoints. Those components are deliberately not simulated because NAT Gateways
create ongoing charges and application egress requirements vary.

## Load Balancing and Health

The internet-facing Application Load Balancer spans both public subnets. It forwards
HTTP traffic to a target group on application port `8080`.

The target group checks `/health` and treats HTTP `200` as healthy. During a failure:

1. The instance stops responding.
2. The health check marks it unhealthy.
3. The target group removes it from routing.
4. Healthy targets continue serving requests.
5. Auto Scaling launches a replacement.
6. The replacement registers after becoming healthy.

Production traffic should use HTTPS with a reviewed TLS policy and managed
certificate. HTTP is retained here to keep the local explanation focused and avoid
implying that a real certificate exists.

## Compute and Auto Scaling

Two `t3.micro` application instances begin in service, one per private subnet. They
have private IP addresses, no public IP addresses, and no public SSH rule.

The Auto Scaling Group uses:

- Minimum capacity: 2
- Desired capacity: 2
- Maximum capacity: 4
- ELB-aware health checks
- Private subnet placement across both zones
- A shared launch-template identifier

Instances are treated as replaceable. The simulation never depends on changing one
server manually.

## Security and Identity

The ALB security group accepts public application traffic. The application security
group accepts port `8080` only when the source is the ALB security group.

EC2 uses an IAM role instead of embedded access keys. Its modeled permission allows
only `s3:GetObject` for one application prefix in the artifacts bucket.

The production launch-template guidance requires:

- IMDSv2
- Encrypted EBS
- No public IPv4 address
- Reviewed AMI versions
- Temporary IAM role credentials

See [security.md](security.md) for the complete control review.

## Storage

The S3 model represents a private artifacts bucket with:

- Public access blocked
- AES-256 server-side encryption
- Versioning enabled
- A 30-day lifecycle expiration example

The lifecycle value is educational. Production retention must reflect legal,
recovery, audit, and business requirements.

## Monitoring

Three CloudWatch-style alarms model:

- High EC2 CPU utilization
- Unhealthy ALB targets
- Insufficient Auto Scaling capacity

The Monitoring dashboard derives CPU, requests, healthy hosts, response time, alarm
history, and recovery state from snapshots. No CloudWatch endpoint is contacted.

## Architecture Validation

Before a simulation runs, validation checks important invariants:

- Globally unique, non-empty resource identifiers
- Valid, non-overlapping subnet CIDRs inside the VPC
- Matching public/private subnet coverage across two zones
- Correct route-table associations
- No direct Internet Gateway route or public IP assignment for private subnets
- Multi-AZ ALB and Auto Scaling placement
- Private EC2 placement and consistent launch-template use
- ALB-only application ingress
- Least-privilege IAM constraints
- Private, encrypted, versioned S3 storage
- Valid tracked alarm metrics and evaluation settings

Invalid architecture state fails early with consolidated, actionable messages.

## Production Differences

A real implementation would additionally require:

- Provider and remote-state configuration
- Controlled AWS authentication and deployment roles
- HTTPS, certificates, DNS, and security headers
- NAT or VPC endpoint decisions
- Central logs, notifications, dashboards, and retention
- Patch and AMI lifecycle management
- WAF, backup, disaster-recovery, and incident procedures
- Current cost estimation and organizational security review

Those responsibilities are explained but intentionally not performed by the public
simulator.
