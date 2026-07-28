# Educational Terraform Configuration

This directory is a reviewable Infrastructure as Code artifact for the architecture
shown by the simulator. The Streamlit application reads none of these files and
never installs, initializes, validates, plans, applies, or destroys Terraform.

The configuration is intentionally safe for public study:

- It contains no credentials, account numbers, remote backend, or real resource IDs.
- Example variable files use fake AMI and bucket values.
- Provider credentials are not configured.
- The CI workflow does not install Terraform or call AWS.
- Running this configuration is outside the portfolio simulator's supported flow.

## File Map

| File | Educational purpose |
|---|---|
| `versions.tf` | Terraform and AWS provider version constraints |
| `providers.tf` | Region and consistent demonstration tags |
| `variables.tf` | Typed, validated architecture inputs |
| `network.tf` | VPC, Internet Gateway, multi-AZ subnets, routes, and S3 endpoint |
| `security.tf` | ALB-to-application trust and restricted S3 egress |
| `alb.tf` | Application Load Balancer, target group, health check, and listener |
| `compute.tf` | Hardened launch template, Auto Scaling Group, and scaling policy |
| `iam.tf` | EC2 trust, scoped S3 read policy, and instance profile |
| `storage.tf` | Private, encrypted, versioned S3 with lifecycle management |
| `monitoring.tf` | CPU, unhealthy-target, and capacity alarms |
| `outputs.tf` | Useful example infrastructure outputs |
| `examples/demo.tfvars` | Fake low-capacity demonstration values |
| `examples/production.tfvars` | Fake production-shaped capacity values |
| `tests/infrastructure.tftest.hcl` | Display-only mocked Terraform test examples |

## Production Caveats

A real deployment needs explicit authorization, a reviewed and current AMI,
globally unique storage naming, HTTPS and certificate configuration, remote state,
deployment roles, budgets, current price analysis, logging destinations, security
approval, and a reviewed Terraform plan.

The public portfolio experience deliberately avoids that operational path so it can
remain free, offline, and credential-free.
