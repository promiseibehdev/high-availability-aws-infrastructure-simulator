# Recruiter Guide

## What This Project Demonstrates

The High-Availability AWS Infrastructure Simulator demonstrates cloud architecture
reasoning rather than access to an AWS account. It combines:

- AWS networking and multi-AZ design
- Load balancing and health checks
- Auto Scaling and failure recovery
- IAM and security-group least privilege
- Monitoring and operational explanation
- Cost-aware architecture decisions
- Terraform knowledge
- Python modeling, testing, and CI
- Clear technical communication

Everything runs as a free, offline simulation. No cloud resource is hidden behind
the interface.

## Recommended Five-Minute Walkthrough

### 1. Start on the landing page

Confirm the simulation-only notice and select **Start Guided Tour**.

Look for:

- A clear project purpose
- Immediate disclosure that no AWS environment is connected
- Simple entry points for technical and non-technical visitors

### 2. Replay an EC2 failure

Select **Next event** one step at a time.

Observe:

- The instance failure
- ALB health-check failure
- Target deregistration
- Auto Scaling replacement
- Target registration
- Restored multi-AZ capacity

The topology, timeline, status, metrics, and alarms all refer to the same immutable
snapshot.

### 3. Inspect a resource

Choose an ALB, private subnet, security group, EC2 instance, IAM role, or S3 bucket
from **Resource explorer**.

Look for:

- Resource purpose
- Current simulated status
- Important architecture attributes
- Clear distinction between public and private components

### 4. Open Monitoring and Security Review

The Monitoring tab shows derived CPU, requests, healthy hosts, response time, alarms,
and recovery status.

The Security Review shows the intended trust path and explains why the design uses:

- Private EC2 instances
- ALB-only ingress
- Security-group references
- No public SSH
- IMDSv2
- Least-privilege IAM
- Encrypted, private S3

### 5. Open Terraform Explorer

The currently selected resource automatically maps to matching HCL. Review its
dependencies, important arguments, security considerations, and best practices.

The lifecycle section explains Terraform commands but never executes them.

## Suggested Deeper Scenarios

### Traffic spike

Use this scenario to discuss:

- CPU-based warning signals
- Scale-out capacity across both zones
- Recovery and conservative scale-in
- Why scaling policy design affects availability and cost

### Availability Zone outage

Use this scenario to discuss:

- Failure-domain isolation
- Healthy-zone traffic routing
- Temporary failover capacity
- Restoring balanced multi-AZ placement after recovery

## Skills Represented

| Skill | Evidence in the project |
|---|---|
| AWS architecture | Multi-AZ VPC, ALB, ASG, EC2, IAM, S3, CloudWatch |
| Networking | CIDRs, routing, public/private subnet separation |
| High availability | Health checks, failover, replacement, rebalance |
| Security | SG chaining, private compute, IAM scope, encryption |
| Terraform | Resource-level HCL, dependencies, lifecycle education |
| Observability | Metrics, alarms, transitions, recovery status |
| Cost awareness | Static estimates, exclusions, optimization choices |
| Python engineering | Typed models, deterministic engine, immutable snapshots |
| Testing | Unit, scenario, UI, security, deterministic, and offline tests |
| CI | Linux Ruff, pytest, and offline-safety workflow |

## Useful Interview Questions

The project supports discussion of:

- What makes a subnet public?
- Why place the ALB and EC2 instances in different subnet tiers?
- How do ALB health checks and Auto Scaling replacement interact?
- What happens when one Availability Zone fails?
- Why use a security-group reference instead of a broad CIDR?
- Why should EC2 use an IAM role rather than access keys?
- Which resources are likely to dominate cost in a small HA architecture?
- How would the design change for HTTPS, a database, or private egress?
- Why are deterministic snapshots valuable for tests and demos?
- What is intentionally missing from the simulation?

## How to Evaluate the Work

Strong signals include:

- Architectural decisions are explained, not merely named.
- Failure and recovery follow a coherent sequence.
- Security boundaries are enforced by validation and tests.
- Simulated output is never presented as live AWS data.
- Cost estimates state their date, assumptions, and exclusions.
- Terraform examples teach dependencies without creating an execution path.
- The application recovers safely from invalid session state.
- Dependencies remain small and the runtime stays offline.

## Important Limitations

This is not proof that the architecture has been deployed or benchmarked on AWS.
It does not demonstrate real AWS console access, production operations, live
CloudWatch data, Terraform provider validation, or an external security audit.

Its purpose is to make architecture knowledge and engineering quality directly
inspectable without requiring cloud spend.

## Screenshot Capture Plan

After deployment, capture:

1. Landing Page
2. Simulator Dashboard
3. Architecture View
4. Monitoring Dashboard
5. Security Review
6. Cost Awareness
7. Terraform Explorer
8. Guided Tour
9. Mobile View

Use consistent sample scenarios, remove browser distractions, verify simulation
labels remain visible, and include descriptive alternative text when embedding the
images in project pages.
