"""Admin CLI: user bootstrap (`python -m c360.cli create-user ...`)."""
from __future__ import annotations

import typer
from sqlalchemy.orm import Session

from .db import get_sessionmaker
from .repositories.users import create_user, get_user_by_email
from .security.hashing import hash_password

app = typer.Typer(add_completion=False)


@app.command()
def create_admin(email: str = typer.Option(...), password: str = typer.Option(...),
                  full_name: str = typer.Option("Administrator")) -> None:
    db: Session = get_sessionmaker()()
    try:
        if get_user_by_email(db, email):
            typer.echo(f"User {email} already exists.")
            return
        user_id = create_user(db, email, hash_password(password), full_name, ["admin"])
        typer.echo(f"Created admin user {email} (id={user_id})")
    finally:
        db.close()


@app.command()
def create_user_cmd(email: str = typer.Option(...), password: str = typer.Option(...),
                     full_name: str = typer.Option(""), role: str = typer.Option("viewer")) -> None:
    db: Session = get_sessionmaker()()
    try:
        if get_user_by_email(db, email):
            typer.echo(f"User {email} already exists.")
            return
        user_id = create_user(db, email, hash_password(password), full_name, [role])
        typer.echo(f"Created user {email} with role {role} (id={user_id})")
    finally:
        db.close()


if __name__ == "__main__":
    app()
