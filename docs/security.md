# Security Guide

## Security Scope

This project demonstrates security architecture; it is not connected to an AWS
account and does not perform a live security assessment. All controls, findings,
and evidence displayed in the interface describe the local model.

The simulator requires no AWS credentials, API keys, provider authentication,
remote state, network client, or subprocess.

## Trust Boundary

The intended application path is:

```text
Public client
  → ALB listener
  → ALB security group
  → Application security group on port 8080
  → Private EC2 instance
  → Temporary IAM role
  → Approved S3 object prefix
```

Direct public access to EC2 or S3 is not part of the design.

## Reviewed Controls

### VPC isolation

All modeled resources belong to one known VPC boundary. Subnet CIDRs must remain
inside it and must not overlap.

**Reason:** Explicit address, routing, and ownership boundaries reduce accidental
connectivity and make reviews easier.

### Public and private subnet separation

ALB nodes use public subnets. EC2 application instances use private subnets without
public IP addresses or direct Internet Gateway routes.

**Reason:** Public entry points and application compute have different exposure
requirements.

### Security-group chaining

The application security group accepts port `8080` only from the ALB security group.
It does not accept application traffic from `0.0.0.0/0`.

**Reason:** Referencing the expected source group is narrower and more maintainable
than allowing a broad network range.

### ALB-only ingress

Users access the managed load-balancing tier rather than individual instances.
Health checks remove unhealthy targets from the routing path.

**Reason:** One controlled entry point reduces exposure and separates clients from
replaceable compute.

### No public SSH

The model contains no public port `22` rule and gives EC2 no public address.

**Reason:** Routine administration should not require a permanently exposed
management port. A real environment could use a controlled systems-management
service with audited access.

### Least-privilege IAM

The EC2 role allows only `s3:GetObject` for an application object prefix. It uses
role-based temporary credentials rather than embedded keys.

**Reason:** A workload compromise should not automatically grant unrelated account
permissions.

### IMDSv2

The production launch-template example requires metadata session tokens.

**Reason:** IMDSv2 reduces exposure to basic metadata-request abuse, including common
server-side request forgery paths.

### Encryption at rest

S3 encryption is represented in the model. The launch-template guidance enables
encrypted EBS.

**Reason:** Encryption reduces exposure if storage media, objects, or snapshots are
accessed outside the intended path.

### Private, protected S3

Public access is blocked, encryption and versioning are enabled, and IAM access is
resource-scoped.

**Reason:** Application artifacts should not become anonymous public content.

### Monitoring and recovery

Alarms surface high CPU, unhealthy targets, and insufficient capacity.

**Reason:** Preventive controls need detection and a clear recovery path.

## Common Misconfigurations

| Misconfiguration | Risk | Safer design |
|---|---|---|
| Public SSH from anywhere | Brute-force and administrative exposure | No public SSH; use controlled management |
| Public EC2 application servers | Bypasses the intended ALB trust path | Private subnets and ALB-only ingress |
| Wildcard IAM permissions | Workload compromise gains excessive reach | Scope actions and resource ARNs |
| Public or unencrypted S3 | Artifact disclosure or modification | Public block, encryption, versioning, narrow IAM |
| Private subnet routed to an IGW | Undermines the isolation boundary | Direct IGW routes only in public route tables |

## Architecture Validation

The local validator rejects:

- Duplicate or empty resource identifiers
- Invalid or overlapping network ranges
- Private subnets with public addressing or direct IGW routing
- Public placement of application instances
- ALB or Auto Scaling designs that do not span two zones
- Application ingress from public CIDRs
- Missing ALB-to-application security-group trust
- IAM wildcard actions or global resources
- Non-EC2 role trust or unrelated IAM actions
- Public, unencrypted, unversioned, or non-expiring modeled storage
- Missing, duplicated, or internally inconsistent alarms

Validation is not a substitute for AWS Config, IAM Access Analyzer, Security Hub,
GuardDuty, Inspector, penetration testing, or an organizational security review.

## Secret and Credential Safety

Repository protections ignore:

- `.env` files
- Streamlit secrets and credentials
- `.aws` credential directories
- private-key files
- Terraform state, plans, overrides, and non-example variable files

Automated tests scan for common AWS access-key, account ARN, and private-key
patterns. Runtime source is also checked for AWS SDKs, HTTP clients, sockets,
subprocesses, shell execution, credentials, and external URLs.

No scanner can guarantee that every possible secret is detected. Contributors must
still review changes before publishing.

## Terraform Safety

HCL in the interface and `terraform/` directory is educational. The application
does not install or invoke Terraform and does not configure provider authentication.

The CI workflow installs only Python dependencies and runs Ruff, pytest, and
offline-safety tests. It does not run `terraform init`, `plan`, `apply`, or
`destroy`, and it does not call the AWS CLI.

## Production Security Additions

A real environment should consider:

- HTTPS, managed certificates, DNS, and secure headers
- WAF rules and rate limiting
- Centralized immutable logs and alert routing
- Systems Manager or equivalent controlled administration
- KMS key policy and rotation requirements
- VPC endpoints and carefully designed egress
- Patch, AMI, vulnerability, and dependency management
- AWS Organizations service-control policies
- Backup, incident response, and disaster-recovery exercises
- Threat modeling and independent security review

These controls require project-specific requirements and authorization, so they are
not presented as active in the simulator.
