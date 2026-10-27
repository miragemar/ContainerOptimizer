from pathlib import Path
import tomllib


STACK_FILES = {
    "Python": [
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "setup.py",
    ],
    "Node.js": ["package.json"],
    "Go": ["go.mod"],
    "Rust": ["Cargo.toml"],
    "Java (Maven)": ["pom.xml"],
    ".NET": ["*.csproj", "*.sln"],
}

DEPENDENCY_FILES = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
]

ENTRYPOINT_CANDIDATES = [
    "main.py",
    "app.py",
    "server.py",
    "manage.py",
    "index.js",
    "server.js",
    "app.js",
    "main.go",
    "src/main.rs",
]


def find_existing_files(root: Path, filenames: list[str]) -> list[str]:
    found = []

    for filename in filenames:
        candidate = root / filename

        if candidate.is_file():
            found.append(filename)
        else:
            found.extend(
                str(path.relative_to(root))
                for path in root.glob(filename)
                if path.is_file()
            )

    return sorted(set(found))


def read_python_scripts(root: Path) -> dict[str, str]:
    """Read CLI scripts declared in pyproject.toml."""
    pyproject = root / "pyproject.toml"

    if not pyproject.is_file():
        return {}

    try:
        with pyproject.open("rb") as file:
            config = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return {}

    scripts = config.get("project", {}).get("scripts", {})

    if not isinstance(scripts, dict):
        return {}

    return {
        name: target
        for name, target in scripts.items()
        if isinstance(name, str) and isinstance(target, str)
    }


def analyze_project(project_path: str = ".") -> dict:
    root = Path(project_path).resolve()

    if not root.is_dir():
        raise NotADirectoryError(
            f"Project directory does not exist: {root}"
        )

    detected_stacks = []

    for stack, filenames in STACK_FILES.items():
        if find_existing_files(root, filenames):
            detected_stacks.append(stack)

    dependency_files = find_existing_files(root, DEPENDENCY_FILES)

    entrypoints = [
        filename
        for filename in ENTRYPOINT_CANDIDATES
        if (root / filename).is_file()
    ]

    python_scripts = read_python_scripts(root)

    dockerfile = root / "Dockerfile"
    dockerignore = root / ".dockerignore"

    compose_file = root / "compose.yaml"
    if not compose_file.is_file():
        compose_file = root / "docker-compose.yml"

    return {
        "project_path": str(root),
        "detected_stacks": detected_stacks,
        "dependency_files": dependency_files,
        "entrypoint_candidates": entrypoints,
        "python_cli_scripts": python_scripts,
        "dockerfile_exists": dockerfile.is_file(),
        "dockerignore_exists": dockerignore.is_file(),
        "compose_file_exists": compose_file.is_file(),
    }
