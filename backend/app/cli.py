"""Admin commands. Usage:

uv run python -m app.cli create-user --email a@b.c --name "Full Name" --role admin
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core import audit
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import User
from app.models.user import ROLES

MIN_PASSWORD_LENGTH = 12


def create_user(args: argparse.Namespace) -> None:
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if getpass.getpass("Repeat password: ") != password:
        sys.exit("Passwords do not match.")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == args.email)):
            sys.exit(f"A user with email {args.email} already exists.")

        user = User(
            email=args.email,
            password_hash=hash_password(password),
            full_name=args.name,
            role=args.role,
        )
        db.add(user)
        db.flush()  # assigns user.id
        audit.record(
            db,
            "user.created",
            target_type="user",
            target_id=str(user.id),
            metadata={"email": user.email, "role": user.role, "via": "cli"},
        )
        db.commit()
        print(f"Created {user.role} {user.email} ({user.id})")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("create-user", help="Create a user account")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", choices=ROLES, default="viewer")
    p.set_defaults(func=create_user)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
