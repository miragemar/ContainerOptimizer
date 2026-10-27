
import pytest

from containeroptimizer.builder import (
    review_dockerfile,
    save_dockerfile,
    validate_dockerfile_content,
)


def test_validates_basic_dockerfile():
    content = (
        "FROM python:3.12-slim\n"
        "WORKDIR /app\n"
        "CMD [\"python\", \"app.py\"]\n"
    )

    assert validate_dockerfile_content(content) == []


def test_rejects_empty_content():
    errors = validate_dockerfile_content("")

    assert errors
    assert "empty" in errors[0].lower()


def test_rejects_missing_from():
    content = 'CMD ["python", "app.py"]\n'

    errors = validate_dockerfile_content(content)

    assert any("FROM" in error for error in errors)


def test_rejects_missing_command():
    content = "FROM python:3.12-slim\n"

    errors = validate_dockerfile_content(content)

    assert any(
        "CMD or ENTRYPOINT" in error
        for error in errors
    )


def test_saves_dockerfile(tmp_path):
    destination = tmp_path / "Dockerfile"
    content = 'FROM python:3.12-slim\nCMD ["python", "app.py"]'

    saved_path = save_dockerfile(
        content,
        output_path=str(destination),
    )

    assert saved_path.is_file()
    assert saved_path.read_text(encoding="utf-8").endswith("\n")


def test_does_not_overwrite_existing_file(tmp_path):
    destination = tmp_path / "Dockerfile"
    destination.write_text("existing content\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        save_dockerfile(
            'FROM python:3.12-slim\nCMD ["python", "app.py"]',
            output_path=str(destination),
        )

    assert destination.read_text(encoding="utf-8") == (
        "existing content\n"
    )


def test_review_includes_security_findings():
    content = (
        "FROM python:latest\n"
        'CMD ["python", "app.py"]\n'
    )

    result = review_dockerfile(content)

    assert result["valid"] is True
    assert result["security_findings_count"] > 0
