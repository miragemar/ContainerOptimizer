
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


def generate_dockerfile(
    project_context: dict,
    model: str | None = None,
) -> str:
    """Generate a Dockerfile using the Gemini Interactions API."""

    # Load the project's .env file without printing secrets.
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Configure it in the project's local .env file."
        )

    model_name = (
        model
        or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    )

    prompt = f"""
You are a senior DevSecOps engineer generating a functional Dockerfile.

Generate a Dockerfile for the supplied project metadata.

Requirements:
- Use an appropriate, specific base image tag.
- Use multi-stage builds when they provide a real benefit.
- Prefer reproducible dependency installation.
- Run the application as a non-root user when supported.
- Do not copy secrets into the image.
- Do not invent dependencies, filenames, modules, or commands.
- Use only files and startup commands supported by the metadata.
- If python_cli_scripts contains a detected CLI script, prefer using
  its registered command as the application startup command when
  appropriate.
- For example, if python_cli_scripts contains
  {{"demo-greeter": "demo_app.cli:main"}}, use
  CMD ["demo-greeter"] when appropriate.
- Do not assume every Python project is a CLI application.
- If pyproject.toml describes an installable Python package, install
  the project so its registered CLI commands become available.
- Ensure the final image includes the application and runtime
  dependencies needed by its startup command.
- Copy only the files required to build and run the application.
- Do not copy .env files, credentials, or other secrets.
- If the startup command cannot be determined safely, do not invent
  one. Explain the uncertainty in a Dockerfile comment.
- Return only Dockerfile content, without Markdown fences or prose.

Project metadata:
{project_context}
"""

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=20000,
            retry_options=types.HttpRetryOptions(
                attempts=1,
            ),
        ),
    )

    try:
        response = client.interactions.create(
            model=model_name,
            input=prompt,
        )
    except Exception as error:
        raise RuntimeError(
            f"Gemini request failed ({type(error).__name__}). "
            "Check the model, API access, quota, and network connection."
        ) from None

    content = response.output_text

    if not content or not content.strip():
        raise RuntimeError("Gemini returned an empty response.")

    content = content.strip()

    # Remove Markdown fences if the model returns them anyway.
    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    if not content:
        raise RuntimeError("Gemini returned an empty Dockerfile.")

    return content + "\n"
