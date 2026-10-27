
import asyncio
import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header, Input, Static, TextArea

from containeroptimizer.ai.gemini import generate_dockerfile
from containeroptimizer.analyzer import analyze_project
from containeroptimizer.builder import (
    review_dockerfile,
    save_dockerfile,
    validate_dockerfile_content,
)


LOGO = r"""
  ___   __    __  _   _____    __    _   __  _   ___   ___    __    ___   _____   _   __ __   _    ___   ___   ___
 / _/  /__\  |  \| | |_   _|  /  \  | | |  \| | | __| | _ \  /__\  | _,\ |_   _| | | |  V  | | |  |_  | | __| | _ \
| \__ | \/ | | | ' |   | |   | /\ | | | | | ' | | _|  | v / | \/ | | v_/   | |   | | | \_/ | | |   / /  | _|  | v /
 \__/  \__/  |_|\__|   |_|   |_||_| |_| |_|\__| |___| |_|_\  \__/  |_|     |_|   |_| |_| |_| |_|  |___| |___| |_|_\
"""


class ContainerOptimizerApp(App):
    TITLE = "ContainerOptimizer"
    SUB_TITLE = "AI Dockerfile Builder & Security Auditor"

    CSS = """
    Screen {
        padding: 1 2;
    }

    #logo {
        color: cyan;
        text-align: center;
        height: 8;
        content-align: center middle;
    }

    #project-label {
        margin-top: 1;
    }

    #project-path {
        margin-bottom: 1;
    }

    #actions {
        height: auto;
        margin-bottom: 1;
    }

    #actions Button {
        width: 1fr;
        margin-right: 1;
    }

    #output {
        height: 1fr;
        border: round $accent;
    }

    #status {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+l", "clear_output", "Clear output"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(LOGO, id="logo")
        yield Static("Project directory:", id="project-label")
        yield Input(".", placeholder="/path/to/your/project", id="project-path")

        with Horizontal(id="actions"):
            yield Button("Analyze", variant="primary", id="analyze")
            yield Button("Generate Dockerfile", variant="success", id="generate")
            yield Button("Security Audit", variant="warning", id="audit")
            yield Button("Clear", id="clear")

        yield TextArea(
            "Welcome to ContainerOptimizer!\n\n"
            "Enter a project directory and select an action.\n\n"
            "Analyze: inspect project metadata.\n"
            "Generate: generate and validate a Dockerfile using Gemini.\n"
            "Security Audit: review the project's existing Dockerfile.\n",
            read_only=True,
            id="output",
        )
        yield Static("Ready", id="status")
        yield Footer()

    def show_output(self, message: str) -> None:
        self.query_one("#output", TextArea).text = message

    def set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def get_project_path(self) -> Path:
        value = self.query_one("#project-path", Input).value.strip()

        if not value:
            raise ValueError("Enter a project directory path.")

        root = Path(value).expanduser().resolve()

        if not root.is_dir():
            raise NotADirectoryError(
                f"Project directory does not exist: {root}"
            )

        return root

    @staticmethod
    def build_safe_context(analysis: dict) -> dict:
        """Send only allowlisted project metadata to Gemini."""
        return {
            "detected_stacks": analysis["detected_stacks"],
            "dependency_files": analysis["dependency_files"],
            "entrypoint_candidates": analysis["entrypoint_candidates"],
            "python_cli_scripts": analysis["python_cli_scripts"],
            "dockerfile_exists": analysis["dockerfile_exists"],
            "dockerignore_exists": analysis["dockerignore_exists"],
            "compose_file_exists": analysis["compose_file_exists"],
        }

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id

        if action == "clear":
            self.show_output("")
            self.set_status("Output cleared")
            return

        try:
            root = self.get_project_path()
        except (ValueError, NotADirectoryError) as error:
            self.show_output(f"Input error:\n{error}")
            self.set_status("Check project path")
            return

        self.set_status("Working...")
        self.show_output(
            f"Action: {action}\n"
            f"Project: {root}\n\n"
            "Please wait..."
        )

        try:
            if action == "analyze":
                result = await asyncio.to_thread(
                    analyze_project,
                    str(root),
                )

                output = json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False,
                )

            elif action == "audit":
                dockerfile = root / "Dockerfile"

                if not dockerfile.is_file():
                    raise FileNotFoundError(
                        f"No Dockerfile found at {dockerfile}"
                    )

                content = await asyncio.to_thread(
                    dockerfile.read_text,
                    encoding="utf-8",
                )

                review = await asyncio.to_thread(
                    review_dockerfile,
                    content,
                )

                output = json.dumps(
                    review,
                    indent=2,
                    ensure_ascii=False,
                )

            elif action == "generate":
                analysis = await asyncio.to_thread(
                    analyze_project,
                    str(root),
                )

                safe_context = self.build_safe_context(analysis)

                # The API call runs in a background thread so the UI
                # remains responsive while Gemini is processing.
                content = await asyncio.to_thread(
                    generate_dockerfile,
                    safe_context,
                )

                errors = validate_dockerfile_content(content)

                if errors:
                    raise ValueError(
                        "Generated Dockerfile failed validation:\n- "
                        + "\n- ".join(errors)
                    )

                # Do not overwrite an existing generated file or Dockerfile.
                destination = root / "Dockerfile.generated"

                saved_path = await asyncio.to_thread(
                    save_dockerfile,
                    content,
                    str(destination),
                    False,
                )

                output = (
                    "SUCCESS: Dockerfile generated and validated!\n\n"
                    f"Project: {root}\n"
                    f"Saved to: {saved_path}\n\n"
                    "----- Dockerfile.generated -----\n\n"
                    f"{content}"
                )

            else:
                return

            self.show_output(output)
            self.set_status("Completed")

        except Exception as error:
            message = f"{type(error).__name__}:\n{error}"

            self.show_output(
                f"Operation failed\n\n{message}\n\n"
                "Check the project path, file permissions, API key, "
                "model availability, quota, and network connection "
                "as appropriate."
            )
            self.set_status("Operation failed")

    def action_clear_output(self) -> None:
        self.show_output("")
        self.set_status("Output cleared")


def main() -> None:
    ContainerOptimizerApp().run()


if __name__ == "__main__":
    main()
