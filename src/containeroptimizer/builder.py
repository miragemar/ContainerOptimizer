
from pathlib import Path

from containeroptimizer.security.rules import audit_dockerfile


def validate_dockerfile_content(content: str) -> list[str]:
    """Validate basic Dockerfile structure before saving."""
    errors = []

    if not content or not content.strip():
        return ["Generated Dockerfile is empty."]

    instructions = []

    for line in content.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        instructions.append(stripped)

    if not any(
        line.upper().startswith("FROM ")
        for line in instructions
    ):
        errors.append("Dockerfile must contain a FROM instruction.")

    if not any(
        line.upper().startswith("CMD ")
        or line.upper().startswith("ENTRYPOINT ")
        for line in instructions
    ):
        errors.append(
            "Dockerfile should contain CMD or ENTRYPOINT."
        )

    return errors


def save_dockerfile(
    content: str,
    output_path: str = "Dockerfile",
    overwrite: bool = False,
) -> Path:
    """Validate and save Dockerfile content to disk."""
    errors = validate_dockerfile_content(content)

    if errors:
        raise ValueError(
            "Invalid Dockerfile:\n- " + "\n- ".join(errors)
        )

    destination = Path(output_path)

    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"{destination} already exists. "
            "Choose another path or explicitly allow overwrite."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content.rstrip() + "\n", encoding="utf-8")

    return destination


def review_dockerfile(content: str) -> dict:
    """Return structural validation and security audit results."""
    errors = validate_dockerfile_content(content)
    findings = audit_dockerfile(content)

    return {
        "valid": not errors,
        "validation_errors": errors,
        "security_findings_count": len(findings),
        "security_findings": findings,
    }
