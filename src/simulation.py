"""Deterministic, synchronous, and completely offline infrastructure simulation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum

from src.architecture import build_reference_architecture
from src.models import (
    AlarmState,
    ArchitectureState,
    CloudWatchAlarm,
    EC2Instance,
    HealthState,
    InstanceLifecycle,
    ResourceStatus,
)
from src.validation import validate_architecture


class EventType(str, Enum):
    NORMAL_OPERATION = "normal_operation"
    INSTANCE_FAILED = "instance_failed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    TARGET_DEREGISTERED = "target_deregistered"
    REPLACEMENT_LAUNCHED = "replacement_launched"
    TARGET_REGISTERED = "target_registered"
    TRAFFIC_SPIKE = "traffic_spike"
    ALARM_TRIGGERED = "alarm_triggered"
    SCALE_OUT = "scale_out"
    TRAFFIC_NORMALIZED = "traffic_normalized"
    SCALE_IN = "scale_in"
    AVAILABILITY_ZONE_OUTAGE = "availability_zone_outage"
    TRAFFIC_REROUTED = "traffic_rerouted"
    RECOVERY_STARTED = "recovery_started"
    CAPACITY_REBALANCED = "capacity_rebalanced"
    RECOVERY_COMPLETED = "recovery_completed"


@dataclass(frozen=True)
class SimulationEvent:
    """One immutable event in a replayable scenario timeline."""

    timestamp: int
    event_type: EventType
    affected_resource: str
    explanation: str


@dataclass(frozen=True)
class InstanceSnapshot:
    resource_id: str
    availability_zone: str
    subnet_id: str
    lifecycle: InstanceLifecycle
    health: HealthState
    cpu_utilization_percent: float
    request_count: int


@dataclass(frozen=True)
class AlarmSnapshot:
    resource_id: str
    state: AlarmState


@dataclass(frozen=True)
class SimulationSnapshot:
    """Immutable state projection captured after a simulation event."""

    timestamp: int
    label: str
    instances: tuple[InstanceSnapshot, ...]
    registered_target_ids: tuple[str, ...]
    desired_capacity: int
    load_balancer_status: ResourceStatus
    target_group_status: ResourceStatus
    unavailable_zones: frozenset[str]
    request_rate: int
    alarms: tuple[AlarmSnapshot, ...]


@dataclass(frozen=True)
class SimulationResult:
    """Complete deterministic output returned for one scenario run."""

    scenario_name: str
    events: tuple[SimulationEvent, ...]
    snapshots: tuple[SimulationSnapshot, ...]

    def __post_init__(self) -> None:
        if not self.scenario_name.strip():
            raise ValueError("A simulation result requires a scenario name.")
        if not self.snapshots:
            raise ValueError("A simulation result requires an initial snapshot.")
        if len(self.snapshots) != len(self.events) + 1:
            raise ValueError("Each event must have one corresponding state snapshot.")
        if any(
            snapshot.timestamp != event.timestamp
            for event, snapshot in zip(self.events, self.snapshots[1:], strict=True)
        ):
            raise ValueError("Event and snapshot timestamps must remain synchronized.")
        if any(
            current.timestamp < previous.timestamp
            for previous, current in zip(self.snapshots, self.snapshots[1:], strict=False)
        ):
            raise ValueError("Simulation snapshot timestamps must be monotonic.")

    @property
    def final_snapshot(self) -> SimulationSnapshot:
        return self.snapshots[-1]


class SimulationEngine:
    """Apply deterministic transitions to an isolated architecture copy."""

    def __init__(self, initial_state: ArchitectureState | None = None) -> None:
        reference = initial_state or build_reference_architecture()
        validate_architecture(reference)
        self.state = deepcopy(reference)
        self.timestamp = 0
        self.request_rate = 0
        self.unavailable_zones: set[str] = set()
        self._events: list[SimulationEvent] = []
        self._snapshots: list[SimulationSnapshot] = []
        self._replacement_counter = 0
        self._capture_snapshot("initial state")

    def run_normal_operation(self) -> SimulationResult:
        self._establish_normal_operation()
        return self._result("normal_operation")

    def run_instance_failure(self) -> SimulationResult:
        self._establish_normal_operation()
        failed = self.state.instance("i-app-a")
        failed.health = HealthState.UNHEALTHY
        failed.cpu_utilization_percent = 0.0
        self.state.load_balancer.status = ResourceStatus.DEGRADED
        self._emit(
            EventType.INSTANCE_FAILED,
            failed.resource_id,
            "The EC2 application instance stopped responding in Availability Zone A.",
        )

        self._alarm("alarm-unhealthy-hosts").state = AlarmState.ALARM
        self._emit(
            EventType.HEALTH_CHECK_FAILED,
            failed.resource_id,
            "The ALB /health check failed and marked the instance unhealthy.",
        )

        self.state.target_group.registered_instance_ids.remove(failed.resource_id)
        self._emit(
            EventType.TARGET_DEREGISTERED,
            self.state.target_group.resource_id,
            "The target group removed the unhealthy instance from request routing.",
        )

        replacement = self._replace_instance(
            failed_instance=failed,
            subnet_id=failed.subnet_id,
            replacement_prefix="failure",
        )
        self._emit(
            EventType.REPLACEMENT_LAUNCHED,
            replacement.resource_id,
            "Auto Scaling launched a replacement to restore desired capacity.",
        )

        self._activate_and_register(replacement)
        self._emit(
            EventType.TARGET_REGISTERED,
            replacement.resource_id,
            "The replacement passed its health check and joined the target group.",
        )
        self.state.load_balancer.status = ResourceStatus.HEALTHY
        self._alarm("alarm-unhealthy-hosts").state = AlarmState.OK
        self._emit(
            EventType.RECOVERY_COMPLETED,
            self.state.auto_scaling_group.resource_id,
            "Two healthy targets are available again and normal routing is restored.",
        )
        validate_architecture(self.state)
        return self._result("instance_failure")

    def run_traffic_spike(self) -> SimulationResult:
        self._establish_normal_operation()
        self.request_rate = 1_200
        for instance in self.state.healthy_instances:
            instance.cpu_utilization_percent = 86.0
            instance.request_count += 600
        self._emit(
            EventType.TRAFFIC_SPIKE,
            self.state.load_balancer.resource_id,
            "Incoming traffic increased sharply and raised CPU usage across the application tier.",
        )

        self._alarm("alarm-high-cpu").state = AlarmState.ALARM
        self._emit(
            EventType.ALARM_TRIGGERED,
            "alarm-high-cpu",
            "The simulated CloudWatch CPU alarm crossed its 70 percent threshold.",
        )

        new_instances = [
            self._create_instance("subnet-private-a", "scale"),
            self._create_instance("subnet-private-b", "scale"),
        ]
        for instance in new_instances:
            self._add_instance(instance)
            self._activate_and_register(instance)
        self.state.auto_scaling_group.desired_capacity = 4
        self._emit(
            EventType.SCALE_OUT,
            self.state.auto_scaling_group.resource_id,
            "Auto Scaling increased desired capacity from two to four healthy instances.",
        )

        self.request_rate = 120
        for instance in self.state.healthy_instances:
            instance.cpu_utilization_percent = 24.0
        self._alarm("alarm-high-cpu").state = AlarmState.OK
        self._emit(
            EventType.TRAFFIC_NORMALIZED,
            self.state.load_balancer.resource_id,
            "Traffic and CPU utilization returned to normal after capacity increased.",
        )

        for instance in new_instances:
            self._remove_instance(instance)
        self.state.auto_scaling_group.desired_capacity = 2
        self._emit(
            EventType.SCALE_IN,
            self.state.auto_scaling_group.resource_id,
            "After a simulated cooldown, Auto Scaling returned desired capacity to two.",
        )
        validate_architecture(self.state)
        return self._result("traffic_spike")

    def run_availability_zone_outage(self) -> SimulationResult:
        self._establish_normal_operation()
        failed_zone = "us-east-1a"
        self.unavailable_zones.add(failed_zone)
        for subnet in self.state.subnets:
            if subnet.availability_zone == failed_zone:
                subnet.status = ResourceStatus.UNAVAILABLE
        failed_instances = [
            item for item in self.state.instances if item.availability_zone == failed_zone
        ]
        for instance in failed_instances:
            instance.health = HealthState.UNHEALTHY
            instance.cpu_utilization_percent = 0.0
        self.state.load_balancer.status = ResourceStatus.DEGRADED
        self.state.target_group.status = ResourceStatus.DEGRADED
        self._emit(
            EventType.AVAILABILITY_ZONE_OUTAGE,
            failed_zone,
            "Availability Zone A became unavailable, affecting its public and private subnets.",
        )

        self._alarm("alarm-unhealthy-hosts").state = AlarmState.ALARM
        for instance in failed_instances:
            self._emit(
                EventType.HEALTH_CHECK_FAILED,
                instance.resource_id,
                "The ALB health check failed because the target's Availability Zone is unavailable.",
            )
            self.state.target_group.registered_instance_ids.remove(instance.resource_id)
            self._emit(
                EventType.TARGET_DEREGISTERED,
                instance.resource_id,
                "The target group stopped routing requests to the unavailable-zone target.",
            )

        self._emit(
            EventType.TRAFFIC_REROUTED,
            self.state.load_balancer.resource_id,
            "The ALB routed all available traffic to healthy targets in Availability Zone B.",
        )

        replacements = []
        for failed in failed_instances:
            replacement = self._replace_instance(
                failed_instance=failed,
                subnet_id="subnet-private-b",
                replacement_prefix="failover",
            )
            self._activate_and_register(replacement)
            replacements.append(replacement)
            self._emit(
                EventType.REPLACEMENT_LAUNCHED,
                replacement.resource_id,
                "Auto Scaling restored capacity in the healthy Availability Zone.",
            )

        self._emit(
            EventType.TARGET_REGISTERED,
            self.state.target_group.resource_id,
            "The failover capacity passed health checks and joined request routing.",
        )

        self.unavailable_zones.remove(failed_zone)
        for subnet in self.state.subnets:
            if subnet.availability_zone == failed_zone:
                subnet.status = ResourceStatus.HEALTHY
        self._emit(
            EventType.RECOVERY_STARTED,
            failed_zone,
            "Availability Zone A recovered and its network resources became available.",
        )

        for replacement in replacements:
            self._remove_instance(replacement)
        rebalanced = self._create_instance("subnet-private-a", "rebalanced")
        self._add_instance(rebalanced)
        self._activate_and_register(rebalanced)
        self._emit(
            EventType.CAPACITY_REBALANCED,
            self.state.auto_scaling_group.resource_id,
            "Auto Scaling redistributed capacity across both healthy Availability Zones.",
        )

        self.state.load_balancer.status = ResourceStatus.HEALTHY
        self.state.target_group.status = ResourceStatus.HEALTHY
        self._alarm("alarm-unhealthy-hosts").state = AlarmState.OK
        self._emit(
            EventType.RECOVERY_COMPLETED,
            failed_zone,
            "Multi-AZ service, health checks, and balanced routing are fully restored.",
        )
        validate_architecture(self.state)
        return self._result("availability_zone_outage")

    def _establish_normal_operation(self) -> None:
        self.request_rate = 100
        healthy = self.state.healthy_instances
        if not healthy:
            raise RuntimeError(
                "Normal operation requires at least one healthy application instance."
            )
        requests_per_instance = self.request_rate // len(healthy)
        for instance in healthy:
            instance.request_count = requests_per_instance
        self._emit(
            EventType.NORMAL_OPERATION,
            self.state.load_balancer.resource_id,
            "The ALB distributes traffic across two healthy instances in separate Availability Zones.",
            seconds_after=0,
        )

    def _replace_instance(
        self,
        failed_instance: EC2Instance,
        subnet_id: str,
        replacement_prefix: str,
    ) -> EC2Instance:
        self._remove_instance(failed_instance)
        replacement = self._create_instance(subnet_id, replacement_prefix)
        self._add_instance(replacement)
        return replacement

    def _create_instance(self, subnet_id: str, prefix: str) -> EC2Instance:
        self._replacement_counter += 1
        subnet = self.state.subnet(subnet_id)
        host_octet = 10 + self._replacement_counter
        network_prefix = ".".join(subnet.cidr_block.split(".")[:3])
        app_security_group = self.state.instance(
            self.state.auto_scaling_group.instance_ids[0]
        ).security_group_ids
        return EC2Instance(
            resource_id=f"i-{prefix}-{self._replacement_counter:03d}",
            name=f"{prefix}-instance-{self._replacement_counter:03d}",
            subnet_id=subnet.resource_id,
            availability_zone=subnet.availability_zone,
            private_ip=f"{network_prefix}.{host_octet}",
            security_group_ids=list(app_security_group),
            iam_role_id=self.state.iam_role.resource_id,
            launch_template_id=self.state.auto_scaling_group.launch_template_id,
            lifecycle=InstanceLifecycle.PENDING,
            health=HealthState.INITIAL,
            cpu_utilization_percent=0.0,
        )

    def _add_instance(self, instance: EC2Instance) -> None:
        self.state.instances.append(instance)
        self.state.auto_scaling_group.instance_ids.append(instance.resource_id)

    def _activate_and_register(self, instance: EC2Instance) -> None:
        instance.lifecycle = InstanceLifecycle.IN_SERVICE
        instance.health = HealthState.HEALTHY
        instance.cpu_utilization_percent = 12.0
        self.state.target_group.registered_instance_ids.append(instance.resource_id)

    def _remove_instance(self, instance: EC2Instance) -> None:
        instance.lifecycle = InstanceLifecycle.TERMINATED
        instance.health = HealthState.UNHEALTHY
        if instance.resource_id in self.state.target_group.registered_instance_ids:
            self.state.target_group.registered_instance_ids.remove(instance.resource_id)
        if instance.resource_id in self.state.auto_scaling_group.instance_ids:
            self.state.auto_scaling_group.instance_ids.remove(instance.resource_id)
        self.state.instances.remove(instance)

    def _alarm(self, resource_id: str) -> CloudWatchAlarm:
        try:
            return next(
                item
                for item in self.state.cloudwatch.alarms
                if item.resource_id == resource_id
            )
        except StopIteration as exc:
            raise KeyError(f"Unknown simulated alarm: {resource_id}") from exc

    def _emit(
        self,
        event_type: EventType,
        affected_resource: str,
        explanation: str,
        seconds_after: int = 1,
    ) -> None:
        self.timestamp += seconds_after
        self._events.append(
            SimulationEvent(
                timestamp=self.timestamp,
                event_type=event_type,
                affected_resource=affected_resource,
                explanation=explanation,
            )
        )
        self._capture_snapshot(event_type.value)

    def _capture_snapshot(self, label: str) -> None:
        instance_snapshots = tuple(
            InstanceSnapshot(
                resource_id=item.resource_id,
                availability_zone=item.availability_zone,
                subnet_id=item.subnet_id,
                lifecycle=item.lifecycle,
                health=item.health,
                cpu_utilization_percent=item.cpu_utilization_percent,
                request_count=item.request_count,
            )
            for item in sorted(self.state.instances, key=lambda value: value.resource_id)
        )
        alarm_snapshots = tuple(
            AlarmSnapshot(resource_id=item.resource_id, state=item.state)
            for item in sorted(
                self.state.cloudwatch.alarms, key=lambda value: value.resource_id
            )
        )
        self._snapshots.append(
            SimulationSnapshot(
                timestamp=self.timestamp,
                label=label,
                instances=instance_snapshots,
                registered_target_ids=tuple(
                    sorted(self.state.target_group.registered_instance_ids)
                ),
                desired_capacity=self.state.auto_scaling_group.desired_capacity,
                load_balancer_status=self.state.load_balancer.status,
                target_group_status=self.state.target_group.status,
                unavailable_zones=frozenset(self.unavailable_zones),
                request_rate=self.request_rate,
                alarms=alarm_snapshots,
            )
        )

    def _result(self, scenario_name: str) -> SimulationResult:
        return SimulationResult(
            scenario_name=scenario_name,
            events=tuple(self._events),
            snapshots=tuple(self._snapshots),
        )
