# Cost Awareness Guide

## Purpose

Cloud architecture decisions have financial consequences even when individual
resource prices appear small. This guide explains the largest cost drivers in the
production-shaped design while keeping the public simulator free.

All displayed values are **educational estimates**, not AWS quotes. They use static
example assumptions dated July 2026 for US East (N. Virginia). Prices, free
allowances, taxes, and usage vary and may change.

The application does not use the AWS Pricing API or any internet service.

## Example Monthly Estimate

| Category | Example assumption | Educational estimate |
|---|---|---:|
| NAT Gateway | Two gateways for 730 hours; processing excluded | $65.70 |
| Application Load Balancer | One ALB for 730 hours; LCUs excluded | $16.43 |
| EC2 | Two Linux `t3.micro` instances for 730 hours | $15.18 |
| EBS | Two 8 GB `gp3` root volumes | $1.28 |
| CloudWatch | Three standard alarms before allowances | $0.30 |
| Public IPv4 | Four addresses for 730 hours | $14.60 |
| Data transfer | Illustrative 10 GB internet egress | $0.90 |
| **Illustrative total** | Excludes variable charges listed below | **$114.39** |

The total is a teaching example. It must not be used for budgeting or procurement.

## Cost Drivers

### NAT Gateway

NAT Gateways charge for running time and processed data. A resilient per-AZ design
can become the largest fixed item in a small environment.

Cost-aware questions:

- Does the workload require general outbound internet access?
- Can VPC endpoints serve required AWS services?
- Does the resilience requirement justify one gateway per zone?
- Can a short-lived test environment be destroyed between demonstrations?

The simulator models no NAT Gateway and makes no outbound request.

### Application Load Balancer

ALB cost combines running hours and Load Balancer Capacity Units. Rules, new
connections, active connections, and processed bytes can affect usage.

Cost-aware practices include destroying temporary ALBs, consolidating compatible
services carefully, and validating LCU assumptions with real workload data.

### EC2

Compute cost depends on instance family, size, operating system, tenancy, region,
purchase model, and running hours.

Use measurements to right-size. Stop or destroy temporary environments, and consider
commitment discounts only for stable, understood production usage.

### EBS

Volumes can continue charging after compute is removed if deletion settings or
cleanup processes are incorrect. Snapshots and provisioned performance also matter.

Provision only required capacity, encrypt volumes, and identify orphaned volumes and
snapshots.

### CloudWatch

Alarms, custom metrics, dashboards, logs, queries, and retention can each contribute
to cost.

Collect telemetry with a clear purpose, set intentional log retention, and remove
non-actionable alarms rather than reducing necessary observability blindly.

### Public IPv4

Public IPv4 addresses may incur hourly charges. Giving each EC2 instance a public
address also increases the attack surface.

Keep application instances private and remove unused Elastic IP addresses.

### Data Transfer

Cost depends on direction, destination, region, Availability Zone, service, and
volume. Cross-zone, NAT-processed, and internet traffic can combine.

Map actual data flows before estimating and test assumptions against current AWS
documentation.

## Excluded and Variable Costs

The static total excludes or simplifies:

- NAT data processing
- ALB capacity units
- Detailed logs and log ingestion
- Snapshots and backup retention
- DNS, certificates, WAF, databases, queues, and notification services
- Cross-zone and service-specific transfer
- Support plans, marketplace software, taxes, and currency conversion
- Free Tier, promotional credits, and negotiated discounts

## Production Versus Portfolio Strategy

| Production environment | Educational simulator |
|---|---|
| Runs managed AWS resources continuously | Runs local Python state |
| Uses actual traffic and telemetry | Uses deterministic metrics |
| Requires credentials and operations | Requires no AWS account |
| May incur hourly and usage charges | Creates $0 in AWS charges |
| Needs current estimates and budgets | Uses clearly dated teaching values |

The simulator is the permanent portfolio demo. If real infrastructure is later
tested, it should be short-lived, explicitly approved, budget-monitored, and safely
destroyed after validation.

## Responsible Estimation Process

For a real project:

1. Confirm the AWS Region and required availability target.
2. Define expected request, compute, storage, logging, and transfer volumes.
3. Identify fixed hourly and variable usage charges.
4. Use current official pricing and a reviewed calculator estimate.
5. Add budgets, alerts, ownership tags, and expiration expectations.
6. Review the Terraform plan and resource count.
7. Measure actual usage and update the estimate after testing.

Cost awareness is an architecture requirement, not a one-time calculation.
