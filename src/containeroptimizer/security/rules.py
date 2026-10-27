
import re


def audit_dockerfile(dockerfile: str) -> list[dict]:
    """Check a Dockerfile for common security and reliability issues."""
    findings = []
    lines = dockerfile.splitlines()

    def add_finding(
        rule_id: str,
        severity: str,
        line: int | None,
        message: str,
        recommendation: str,
    ) -> None:
        findings.append(
            {
                "rule_id": rule_id,
                "severity": severity,
                "line": line,
                "message": message,
                "recommendation": recommendation,
            }
        )

    from_lines = [
        (number, text.strip())
        for number, text in enumerate(lines, start=1)
        if re.match(r"^\s*FROM\s+", text, re.IGNORECASE)
    ]

    if not from_lines:
        add_finding(
            "CO001",
            "HIGH",
            None,
            "Dockerfile has no FROM instruction.",
            "Specify an appropriate, trusted base image.",
        )

    for number, instruction in from_lines:
        if re.search(r":latest\b", instruction, re.IGNORECASE):
            add_finding(
                "CO002",
                "MEDIUM",
                number,
                "Base image uses the mutable latest tag.",
                "Pin a specific image version; consider a digest "
                "for stronger reproducibility.",
            )

    has_user = any(
        re.match(r"^\s*USER\s+", line, re.IGNORECASE)
        for line in lines
    )

    if not has_user:
        add_finding(
            "CO003",
            "HIGH",
            None,
            "No USER instruction was found.",
            "Create or select an unprivileged user and switch to it "
            "where the application supports it.",
        )

    for number, instruction in enumerate(lines, start=1):
        stripped = instruction.strip()

        if re.match(r"^ADD\s+", stripped, re.IGNORECASE):
            add_finding(
                "CO004",
                "LOW",
                number,
                "ADD instruction found.",
                "Prefer COPY unless you specifically need ADD features "
                "such as extracting a local tar archive.",
            )

        if re.search(r"\bapt-get\s+install\b", stripped):
            if not re.search(r"\bapt-get\s+clean\b", stripped):
                add_finding(
                    "CO005",
                    "LOW",
                    number,
                    "apt-get install may leave package lists or cache "
                    "in the image layer.",
                    "Install packages and remove apt lists in the same "
                    "RUN instruction.",
                )

    has_healthcheck = any(
        re.match(r"^\s*HEALTHCHECK\s+", line, re.IGNORECASE)
        for line in lines
    )

    if not has_healthcheck:
        add_finding(
            "CO006",
            "INFO",
            None,
            "No HEALTHCHECK instruction was found.",
            "Consider a health check if the runtime and deployment "
            "platform benefit from it.",
        )

    return findings
