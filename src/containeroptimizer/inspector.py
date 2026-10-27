
from pathlib import Path


MAX_FILE_SIZE = 100_000  # 100 KB

DEPENDENCY_FILES = {
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
}

SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials",
}


def read_text_file(path: Path) -> str | None:
    """Read a small UTF-8 text file, skipping sensitive or binary files."""
    if path.name in SENSITIVE_NAMES:
        return None

    try:
        if not path.is_file() or path.is_symlink():
            return None

        if path.stat().st_size > MAX_FILE_SIZE:
            return None

        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def inspect_project(project_path: str = ".") -> dict:
    root = Path(project_path).resolve()

    if not root.is_dir():
        raise NotADirectoryError(
            f"Project directory does not exist: {root}"
        )

    result = {
        "dependency_contents": {},
        "dockerfile_contents": None,
        "dockerignore_contents": None,
    }

    for filename in DEPENDENCY_FILES:
        content = read_text_file(root / filename)

        if content is not None:
            result["dependency_contents"][filename] = content

    result["dockerfile_contents"] = read_text_file(
        root / "Dockerfile"
    )
    result["dockerignore_contents"] = read_text_file(
        root / ".dockerignore"
    )

    return result
