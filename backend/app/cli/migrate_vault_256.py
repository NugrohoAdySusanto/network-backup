from __future__ import annotations

import logging
from sqlalchemy import text

from app.core.security import decrypt_secret, encrypt_secret
from app.database import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_vault_256")


def migrate_credentials_to_aes256():
    engine = get_engine()
    migrated_count = 0
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, name, secret_key_encrypted, master_key_encrypted FROM storage_repositories;")
        ).fetchall()

        for row in rows:
            repo_id, name, old_secret, old_master = row[0], row[1], row[2], row[3]

            dec_secret = decrypt_secret(old_secret) if old_secret else ""
            dec_master = decrypt_secret(old_master) if old_master else ""

            new_secret = encrypt_secret(dec_secret) if dec_secret else ""
            new_master = encrypt_secret(dec_master) if dec_master else None

            conn.execute(
                text(
                    "UPDATE storage_repositories "
                    "SET secret_key_encrypted = :sec, master_key_encrypted = :mas "
                    "WHERE id = :id"
                ),
                {"sec": new_secret, "mas": new_master, "id": repo_id},
            )
            migrated_count += 1
            logger.info(
                "Migrated repository '%s' (%s) credentials to AES-256 (length: %d)",
                name,
                repo_id,
                len(new_secret),
            )

        conn.commit()

    logger.info("Successfully migrated %d storage repositories to AES-256.", migrated_count)


if __name__ == "__main__":
    migrate_credentials_to_aes256()
