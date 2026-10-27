import json

from containeroptimizer.analyzer import analyze_project, read_python_scripts


def test_detects_python_cli_script(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "example-app"
version = "0.1.0"

[project.scripts]
example = "example.cli:main"
""".strip(),
        encoding="utf-8",
    )

    scripts = read_python_scripts(tmp_path)

    assert scripts == {"example": "example.cli:main"}


def test_analyze_project_includes_python_cli_scripts(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "example-app"
version = "0.1.0"

[project.scripts]
example = "example.cli:main"
""".strip(),
        encoding="utf-8",
    )

    result = analyze_project(str(tmp_path))

    assert "Python" in result["detected_stacks"]
    assert result["python_cli_scripts"] == {
        "example": "example.cli:main"
    }


def test_missing_pyproject_returns_empty_scripts(tmp_path):
    assert read_python_scripts(tmp_path) == {}


def test_invalid_pyproject_returns_empty_scripts(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "this is not valid TOML = [",
        encoding="utf-8",
    )

    assert read_python_scripts(tmp_path) == {}
