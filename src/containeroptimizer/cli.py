
import argparse
import json
import sys
from pathlib import Path

from containeroptimizer.ai.gemini import generate_dockerfile
from containeroptimizer.analyzer import analyze_project
from containeroptimizer.builder import (
    save_dockerfile,
    validate_dockerfile_content,
)
from containeroptimizer.security.rules import audit_dockerfile


def print_json(data: dict) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def run_analyze(project_path: str) -> int:
    """Analyze project structure without exposing file contents."""
    try:
        result = analyze_project(project_path)
    except (NotADirectoryError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print_json(result)
    return 0


def run_audit(dockerfile_path: str) -> int:
    """Audit a Dockerfile using built-in security rules."""
    path = Path(dockerfile_path)

    if not path.is_file():
        print(f"Error: Dockerfile not found: {path}", file=sys.stderr)
        return 1

    try:
        dockerfile = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(f"Error: Cannot read Dockerfile: {error}", file=sys.stderr)
        return 1

    findings = audit_dockerfile(dockerfile)

    print_json({
        "dockerfile": str(path.resolve()),
        "findings_count": len(findings),
        "findings": findings,
    })
    return 0


def run_generate(
    project_path: str,
    output_path: str,
    overwrite: bool = False,
) -> int:
    """Generate, validate, and save a Dockerfile."""
    try:
        analysis = analyze_project(project_path)

        # Send only allowlisted metadata to Gemini.
        # Do not send raw files, secrets, or absolute local paths.
        safe_context = {
            "detected_stacks": analysis["detected_stacks"],
            "dependency_files": analysis["dependency_files"],
            "entrypoint_candidates": analysis["entrypoint_candidates"],
            "python_cli_scripts": analysis["python_cli_scripts"],
            "dockerfile_exists": analysis["dockerfile_exists"],
            "dockerignore_exists": analysis["dockerignore_exists"],
            "compose_file_exists": analysis["compose_file_exists"],
        }

        content = generate_dockerfile(safe_context)

        errors = validate_dockerfile_content(content)
        if errors:
            print(
                "Generated Dockerfile failed validation:\n- "
                + "\n- ".join(errors),
                file=sys.stderr,
            )
            return 1

        destination = Path(output_path)
        if not destination.is_absolute():
            destination = Path(project_path).resolve() / destination

        saved_path = save_dockerfile(
            content,
            output_path=str(destination),
            overwrite=overwrite,
        )

    except FileExistsError as error:
        print(
            f"{error}\nUse --output Dockerfile.generated "
            "or explicitly pass --overwrite.",
            file=sys.stderr,
        )
        return 1
    except (NotADirectoryError, OSError, ValueError, RuntimeError) as error:
        print(f"Generation failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        # API providers can raise their own exception types.
        print(
            f"Gemini request failed ({type(error).__name__}). "
            "Check your API key, model name, quota, and network connection.",
            file=sys.stderr,
        )
        return 1

    print(f"Dockerfile generated and saved to: {saved_path}")
    print("Note: structural validation is not a guarantee that the image builds securely.")
    return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="containeroptimizer",
        description="AI Dockerfile Builder and Security Auditor",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ContainerOptimizer 0.1.0",
    )

    commands = parser.add_subparsers(dest="command")

    analyze_parser = commands.add_parser(
        "analyze",
        help="Analyze project structure and detect its stack",
    )
    analyze_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project directory",
    )

    audit_parser = commands.add_parser(
        "audit",
        help="Audit a Dockerfile for security issues",
    )
    audit_parser.add_argument(
        "path",
        nargs="?",
        default="Dockerfile",
        help="Path to the Dockerfile",
    )

    generate_parser = commands.add_parser(
        "generate",
        help="Generate a Dockerfile using Gemini AI",
    )
    generate_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project directory to analyze",
    )
    generate_parser.add_argument(
        "--output",
        default="Dockerfile",
        help="Output filename (default: Dockerfile)",
    )
    generate_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "analyze":
        exit_code = run_analyze(args.path)
    elif args.command == "audit":
        exit_code = run_audit(args.path)
    elif args.command == "generate":
        exit_code = run_generate(
            args.path,
            args.output,
            args.overwrite,
        )
    else:
        parser.print_help()
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
