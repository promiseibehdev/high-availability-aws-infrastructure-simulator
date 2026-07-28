import re
from pathlib import Path

import pytest

from src.architecture import build_reference_architecture
from src.models import AlarmState, HealthState
from src.scenarios import ScenarioName, run_scenario
from src.simulation import SimulationResult

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (ROOT / "app.py", *sorted((ROOT / "src").glob("*.py")))


@pytest.mark.parametrize("scenario", list(ScenarioName))
def test_every_scenario_is_a_deterministic_complete_replay(scenario):
    first = run_scenario(scenario)
    second = run_scenario(scenario)

    assert first == second
    assert first is not second
    assert len(first.snapshots) == len(first.events) + 1
    assert first.final_snapshot.load_balancer_status.value == "healthy"
    assert first.final_snapshot.target_group_status.value == "healthy"
    assert all(
        instance.health is HealthState.HEALTHY
        for instance in first.final_snapshot.instances
    )
    assert all(alarm.state is AlarmState.OK for alarm in first.final_snapshot.alarms)


def test_malformed_simulation_results_fail_with_actionable_errors():
    with pytest.raises(ValueError, match="scenario name"):
        SimulationResult("", (), ())
    with pytest.raises(ValueError, match="initial snapshot"):
        SimulationResult("broken", (), ())


def test_resource_lookups_report_unknown_identifiers():
    architecture = build_reference_architecture()

    with pytest.raises(KeyError, match="Unknown subnet resource"):
        architecture.subnet("subnet-missing")
    with pytest.raises(KeyError, match="Unknown EC2 instance resource"):
        architecture.instance("i-missing")


def test_runtime_has_no_cloud_network_or_process_clients():
    source = "\n".join(path.read_text(encoding="utf-8") for path in RUNTIME_FILES).lower()
    forbidden = (
        "import boto3",
        "from boto3",
        "import botocore",
        "import requests",
        "import httpx",
        "import urllib",
        "import socket",
        "import subprocess",
        "os.system",
        "popen(",
        "terraform.exe",
        "aws_access_key_id",
        "aws_secret_access_key",
        "http://",
        "https://",
    )

    assert all(term not in source for term in forbidden)


def test_repository_contains_no_common_live_secret_formats():
    text_files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".ruff_cache" not in path.parts
        and path.suffix not in {".pyc", ".png", ".jpg", ".jpeg"}
    ]
    source = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore") for path in text_files
    )
    patterns = (
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\bASIA[0-9A-Z]{16}\b",
        r"arn:aws:iam::[0-9]{12}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    )

    assert all(re.search(pattern, source) is None for pattern in patterns)


def test_ignore_file_protects_local_credentials_and_state():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for entry in (
        ".env",
        ".streamlit/secrets.toml",
        ".streamlit/credentials.toml",
        ".aws/",
        "*.pem",
        "*.key",
        ".terraform/",
        "*.tfstate",
        "terraform.tfvars",
    ):
        assert entry in ignored


def test_ci_never_installs_or_runs_terraform_or_aws_commands():
    workflow = (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8")
    run_commands = "\n".join(
        line.strip() for line in workflow.splitlines() if line.strip().startswith("run:")
    ).lower()

    assert "terraform " not in run_commands
    assert "aws " not in run_commands
    assert "ruff" in run_commands
    assert "pytest" in run_commands


def test_release_artifacts_contain_no_unfinished_markers():
    release_files = [
        ROOT / "README.md",
        ROOT / "app.py",
        *sorted((ROOT / "src").glob("*.py")),
        *sorted((ROOT / "docs").glob("*.md")),
        *sorted((ROOT / "terraform").rglob("*.*")),
        ROOT / "assets" / "architecture.svg",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in release_files)
    markers = (
        "TO" + "DO",
        "FIX" + "ME",
        "place" + "holder",
        "coming " + "soon",
        "later " + "phase",
        "<repository" + "-url>",
    )

    assert all(marker.lower() not in source.lower() for marker in markers)


def test_all_local_markdown_links_resolve():
    markdown_files = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*.md")),
        ROOT / "terraform" / "README.md",
    ]
    link_pattern = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")

    for document in markdown_files:
        for target in link_pattern.findall(document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (document.parent / target.split("#", maxsplit=1)[0]).resolve()
            assert resolved.exists(), f"Broken link in {document.name}: {target}"


def test_runtime_dependency_footprint_remains_minimal():
    requirements = {
        line.split(">", maxsplit=1)[0].strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert requirements == {"streamlit", "graphviz"}


def test_terraform_examples_use_fake_identifiers_and_complete_files():
    terraform_files = sorted((ROOT / "terraform").rglob("*.tf")) + sorted(
        (ROOT / "terraform").rglob("*.tfvars")
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in terraform_files)

    assert terraform_files
    assert all(path.read_text(encoding="utf-8").strip() for path in terraform_files)
    assert "ami-0123456789abcdef0" in source
    assert re.search(r"arn:aws:iam::[0-9]{12}", source) is None
    assert re.search(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", source) is None
