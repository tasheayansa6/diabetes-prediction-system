from pathlib import Path
import re
import sys


def _latest_migration_file(versions_dir: Path) -> Path | None:
    files = sorted(versions_dir.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _function_body(source: str, fn_name: str) -> str:
    pattern = rf"def {fn_name}\(\):\n((?:    .*\n)*)"
    match = re.search(pattern, source)
    return match.group(1) if match else ""


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    versions_dir = root / "migrations" / "versions"
    if not versions_dir.exists():
        print("ERROR: migrations/versions not found.")
        return 1

    files = sorted(versions_dir.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest = files[0] if files else None
    if not latest:
        print("ERROR: No migration files found in migrations/versions.")
        return 1

    source = latest.read_text(encoding="utf-8")
    upgrade_body = _function_body(source, "upgrade")
    downgrade_body = _function_body(source, "downgrade")

    if not upgrade_body.strip() or upgrade_body.strip() == "pass":
        # If this is the only migration file, warn (bootstrap projects often start this way).
        if len(files) == 1:
            print(f"WARNING: Bootstrap migration '{latest.name}' has an empty upgrade().")
        else:
            print(f"ERROR: Latest migration '{latest.name}' has an empty upgrade().")
            return 1

    if not downgrade_body.strip() or downgrade_body.strip() == "pass":
        print(f"WARNING: Latest migration '{latest.name}' has an empty downgrade().")

    print(f"OK: Migration check passed for '{latest.name}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

