"""Initialise le compte administrateur de démonstration du POC."""

import os

from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker
from werkzeug.security import generate_password_hash

from common.models.users import ADMIN, DIRECTION, SUPER_ADMIN, Users, UsersPasswords


def _database_url() -> URL:
    required_settings = (
        "POSTGRES_USER_SECURE",
        "POSTGRES_PASSWORD_SECURE",
        "POSTGRES_DB_USERS",
    )
    missing_settings = [key for key in required_settings if not os.environ.get(key)]
    if missing_settings:
        raise RuntimeError(
            f"Variables d'environnement manquantes : {', '.join(missing_settings)}."
        )
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER_SECURE"],
        password=os.environ["POSTGRES_PASSWORD_SECURE"],
        host=os.environ.get("POSTGRES_HOST", "db-main"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB_USERS"],
    )


def _active_password(database_session: Session, user_id: int) -> UsersPasswords | None:
    return database_session.scalar(
        select(UsersPasswords).where(
            UsersPasswords.user_id == user_id,
            UsersPasswords.to_date.is_(None),
        )
    )


def main() -> None:
    """Crée ou met à jour le compte POC admin/admin."""
    database_session = sessionmaker(bind=create_engine(_database_url()))()
    try:
        user = database_session.scalar(select(Users).where(Users.username == "admin"))
        if user is None:
            user = Users(
                username="admin",
                email="admin@faiveley.local",
                permissions=f"{ADMIN}{DIRECTION}{SUPER_ADMIN}",
                is_active=True,
                is_locked=False,
            )
            database_session.add(user)
            database_session.flush()
        user.permissions = f"{ADMIN}{DIRECTION}{SUPER_ADMIN}"
        user.is_active = True
        user.is_locked = False
        password = _active_password(database_session, user.id)
        if password is None:
            database_session.add(
                UsersPasswords(
                    user_id=user.id,
                    password_hash=generate_password_hash("admin"),
                )
            )
        else:
            password.password_hash = generate_password_hash("admin")
        database_session.commit()
    finally:
        database_session.close()

    print("Compte POC prêt : utilisateur admin, mot de passe admin.")


if __name__ == "__main__":
    main()
