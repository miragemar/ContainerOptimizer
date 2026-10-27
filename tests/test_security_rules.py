
import pytest

from containeroptimizer.security.rules import audit_dockerfile


def test_detects_latest_base_image():
    dockerfile = "FROM python:latest\n"

    findings = audit_dockerfile(dockerfile)

    assert any(
        finding["rule_id"] == "CO002"
        for finding in findings
    )


def test_detects_missing_user():
    dockerfile = (
        "FROM python:3.12-slim\n"
        "WORKDIR /app\n"
        "CMD [\"python\", \"app.py\"]\n"
    )

    findings = audit_dockerfile(dockerfile)

    assert any(
        finding["rule_id"] == "CO003"
        for finding in findings
    )


def test_detects_missing_healthcheck():
    dockerfile = (
        "FROM python:3.12-slim\n"
        "USER 10001\n"
        "CMD [\"python\", \"app.py\"]\n"
    )

    findings = audit_dockerfile(dockerfile)

    assert any(
        finding["rule_id"] == "CO006"
        for finding in findings
    )


def test_missing_from_instruction():
    findings = audit_dockerfile("WORKDIR /app\n")

    assert any(
        finding["rule_id"] == "CO001"
        for finding in findings
    )


def test_reports_no_findings_for_basic_compliant_file():
    dockerfile = (
        "FROM python:3.12-slim\n"
        "WORKDIR /app\n"
        "COPY app.py .\n"
        "USER 10001\n"
        "HEALTHCHECK CMD python -c \"print('ok')\"\n"
        "CMD [\"python\", \"app.py\"]\n"
    )

    findings = audit_dockerfile(dockerfile)

    assert findings == []


@pytest.mark.parametrize(
    "instruction",
    [
        "ADD app.py /app/",
        "RUN apt-get install -y curl",
    ],
)
def test_detects_avoidable_image_build_issues(instruction):
    dockerfile = (
        "FROM python:3.12-slim\n"
        f"{instruction}\n"
    )

    findings = audit_dockerfile(dockerfile)

    assert findings
