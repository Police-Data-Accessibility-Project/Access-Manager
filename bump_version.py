import subprocess
import sys
import argparse


def run_command(command, check=True):
    """Run a system command."""
    result = subprocess.run(command, shell=True, check=check, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr and result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Bump project version with Poetry and Git.")
    parser.add_argument(
        "bump",
        choices=["patch", "minor", "major"],
        help="Which part to bump.")
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Also create a Git tag.")
    parser.add_argument(
        "--push",
        action="store_true",
        help="Also push commits and tags."
    )

    args = parser.parse_args()

    # 1. Bump the version
    print(f"Bumping version: {args.bump}")
    run_command(f"poetry version {args.bump}")

    # 2. Get the new version
    new_version = run_command("poetry version --short")
    print(f"New version: {new_version}")

    # 3. Stage the relevant files
    run_command("git add pyproject.toml poetry.lock")

    # 4. Commit with message
    commit_message = f"Bump version to {new_version}"
    run_command(f'git commit -m "{commit_message}"')

    # 5. Optionally create a Git tag
    if args.tag:
        run_command(f"git tag v{new_version}")

    # 6. Optionally push changes
    if args.push:
        run_command("git push")
        if args.tag:
            run_command("git push --tags")


if __name__ == "__main__":
    main()
