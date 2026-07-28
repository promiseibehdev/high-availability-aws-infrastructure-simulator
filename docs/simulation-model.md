# Simulation Model

## Overview

The simulator is a deterministic, synchronous state machine written in Python. Each
scenario starts from a fresh reference architecture, applies a known sequence of
events, and returns immutable snapshots for replay.

It uses no scheduler, background service, random input, wall-clock dependency,
network request, AWS SDK, or Terraform process.

## Core Data Types

### Resource models

Mutable dataclasses represent the working infrastructure state: VPC, subnets, route
tables, security groups, ALB, target group, Auto Scaling Group, EC2 instances, IAM,
S3, and alarms.

The engine receives a reference architecture, validates it, and deep-copies it.
This prevents one simulation from modifying the caller’s architecture or another
visitor’s replay.

### Events

Every event contains:

- Integer timestamp
- Event type
- Affected resource identifier
- Human-readable explanation

Event types include normal operation, instance failure, failed health checks, target
deregistration, replacement, registration, traffic spike, alarm activation, scale
out, normalization, scale in, zone outage, traffic rerouting, recovery, rebalance,
and recovery completion.

### Snapshots

Snapshots are frozen dataclasses containing:

- Timestamp and state label
- Immutable instance projections
- Registered target identifiers
- Desired capacity
- Load balancer and target-group status
- Unavailable zones
- Request rate
- Immutable alarm projections

There is one initial snapshot plus one snapshot after every event. Result validation
rejects missing snapshots, mismatched counts, unsynchronized timestamps, or
non-monotonic timelines.

## Deterministic Event Sequencing

The engine increments a logical timestamp instead of reading system time.
Replacement identifiers use a local counter. Instance and alarm collections are
sorted before snapshot capture.

These decisions ensure the same scenario always returns an equal result:

```python
first = run_scenario("traffic_spike")
second = run_scenario("traffic_spike")
assert first == second
```

Determinism makes the guided tour predictable, supports precise regression tests,
and avoids flaky portfolio demonstrations.

## Supported Scenarios

### Normal operation

1. Set request rate to 100.
2. Split requests across two healthy instances.
3. Record healthy load balancer, target group, and alarms.

### EC2 instance failure

1. Establish normal operation.
2. Mark one instance unhealthy.
3. Activate the unhealthy-target alarm.
4. Deregister the failed target.
5. Replace it through Auto Scaling behavior.
6. Register the healthy replacement.
7. Clear the alarm and restore healthy service.

### Traffic spike

1. Establish normal operation.
2. Raise request volume and CPU.
3. Activate the high-CPU alarm.
4. Add two healthy instances across both zones.
5. Normalize traffic and CPU.
6. Clear the alarm.
7. Scale back to two instances.

### Availability Zone outage

1. Establish normal operation.
2. Mark zone A and its resources unavailable.
3. Fail health checks and remove affected targets.
4. Route traffic to healthy zone B.
5. Restore replacement capacity in zone B.
6. Recover zone A.
7. Rebalance instances across both zones.
8. Clear alarms and report recovery complete.

## Replay in the Interface

Streamlit session state stores the selected scenario result and current timeline
index. **Next event** and **Previous** change only the index. They do not rerun or
mutate the simulation result.

**Reset Simulation** returns the current scenario to its initial snapshot. Running a
different scenario creates a completely fresh result.

If session state contains an invalid result or scenario identifier, the UI recovers
to the safe normal-operation scenario.

## Monitoring Projection

Monitoring values are derived from the snapshots already in memory:

- CPU is the mean of instance CPU values.
- Request rate comes directly from the selected snapshot.
- Healthy-host count is calculated from instance health.
- Response time is a deterministic educational formula based on load, host count,
  CPU, and load-balancer health.
- Alarm history compares successive immutable alarm states.

This projection makes operational relationships visible without presenting the
values as real CloudWatch telemetry.

## Reliability Guarantees

Automated tests verify:

- All scenarios start from fresh state.
- All expected event sequences remain stable.
- Every event has complete audit fields.
- Snapshots are immutable.
- Caller-owned architecture is not mutated.
- Every supported scenario is deterministic.
- Final service, target, instance, and alarm health is restored.
- UI controls replay existing state correctly.
- No cloud, network, subprocess, or Terraform execution path exists.

## Intentional Simplifications

The simulator does not model actual elapsed startup time, asynchronous health-check
intervals, eventual consistency, distributed request queues, partial packet loss,
real CloudWatch aggregation, or AWS control-plane failures.

These simplifications keep the experience understandable and repeatable. They must
not be used for capacity planning, availability guarantees, or operational
forecasting.
