"""Dated, static educational AWS cost examples with no pricing API dependency."""

from __future__ import annotations

from dataclasses import dataclass

ESTIMATE_REGION = "US East (N. Virginia)"
ESTIMATE_DATE = "July 2026"
HOURS_PER_MONTH = 730
ESTIMATE_DISCLAIMER = (
    "Educational estimate only. Actual AWS prices vary by region, usage, account "
    "eligibility, taxes, architecture, and future pricing changes."
)


@dataclass(frozen=True)
class CostEstimate:
    service: str
    example_usage: str
    unit_assumption: str
    estimated_monthly_usd: float
    cost_driver: str
    optimization: str


PRODUCTION_COST_ESTIMATES = (
    CostEstimate(
        "NAT Gateway",
        "Two gateways running for 730 hours",
        "$0.045 per gateway-hour; processing excluded",
        65.70,
        "Hourly gateway count plus each GB processed",
        "Avoid NAT in this simulator; use endpoints or fewer gateways only when resilience requirements allow.",
    ),
    CostEstimate(
        "Application Load Balancer",
        "One ALB running for 730 hours",
        "$0.0225 per ALB-hour; LCU usage excluded",
        16.43,
        "Runtime hours and the highest LCU usage dimension",
        "Destroy short-lived test environments and keep routing rules simple.",
    ),
    CostEstimate(
        "EC2",
        "Two Linux t3.micro instances for 730 hours",
        "$0.0104 per instance-hour",
        15.18,
        "Instance family, size, operating system and runtime",
        "Right-size, stop temporary environments and consider eligible savings options for stable production use.",
    ),
    CostEstimate(
        "EBS",
        "Two 8 GB gp3 root volumes",
        "$0.08 per GB-month",
        1.28,
        "Provisioned storage, performance and snapshots",
        "Delete orphaned volumes and snapshots; provision only required capacity.",
    ),
    CostEstimate(
        "CloudWatch",
        "Three standard alarms",
        "$0.10 per alarm-month before allowances",
        0.30,
        "Alarm count, custom metrics, logs and dashboards",
        "Retain only actionable alarms and apply log-retention policies.",
    ),
    CostEstimate(
        "Public IPv4",
        "Four public addresses for 730 hours",
        "$0.005 per address-hour",
        14.60,
        "Number of in-use public IPv4 addresses and runtime",
        "Keep EC2 private and remove unused Elastic IP addresses.",
    ),
    CostEstimate(
        "Data Transfer",
        "Illustrative 10 GB internet egress",
        "$0.09 per GB illustrative first-tier rate",
        0.90,
        "Destination, direction, region and total bytes",
        "Reduce unnecessary cross-zone and internet transfer; validate current transfer allowances.",
    ),
)


def estimated_monthly_total() -> float:
    """Return the sum of the static examples, excluding documented variable charges."""

    return round(sum(item.estimated_monthly_usd for item in PRODUCTION_COST_ESTIMATES), 2)
