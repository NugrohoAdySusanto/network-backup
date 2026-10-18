"""create schema indexes

Revision ID: 009_indexes
Revises: 008_integrations
"""

from alembic import op
import sqlalchemy as sa

revision = "009_indexes"
down_revision = "008_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("uq_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_active_role", "users", ["is_active", "role"], unique=False)

    op.create_index("uq_devices_zabbix_host_id", "devices", ["zabbix_host_id"], unique=True)
    op.create_index("ix_devices_source_present", "devices", ["source_present"], unique=False)
    op.create_index("ix_devices_availability_status", "devices", ["availability_status"], unique=False)
    op.create_index("ix_devices_hostname", "devices", ["hostname"], unique=False)

    op.create_index(
        "uq_enabled_daily_time",
        "device_backup_settings",
        ["daily_time"],
        unique=True,
        postgresql_where=sa.text("schedule_enabled = true"),
    )
    op.create_index(
        "ix_device_backup_settings_next_run",
        "device_backup_settings",
        ["next_run_at"],
        unique=False,
        postgresql_where=sa.text("schedule_enabled = true"),
    )

    op.create_index(
        "ix_backup_jobs_device_created",
        "backup_jobs",
        ["device_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_backup_jobs_state", "backup_jobs", ["state"], unique=False)
    op.create_index(
        "ix_backup_jobs_created",
        "backup_jobs",
        [sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_backup_jobs_scheduled_for",
        "backup_jobs",
        ["scheduled_for"],
        unique=False,
    )
    op.create_index(
        "ix_backup_jobs_device_success",
        "backup_jobs",
        ["device_id", sa.text("finished_at DESC")],
        unique=False,
        postgresql_where=sa.text(
            "state IN ('SUCCESS_CHANGED', 'SUCCESS_NO_CHANGE')"
        ),
    )

    op.create_index(
        "uq_config_object_content",
        "config_objects",
        ["device_id", "content_sha256"],
        unique=True,
    )
    op.create_index(
        "uq_config_object_s3_key",
        "config_objects",
        ["s3_bucket", "s3_key"],
        unique=True,
    )
    op.create_index(
        "ix_config_objects_storage_status",
        "config_objects",
        ["storage_status"],
        unique=False,
    )

    op.create_index(
        "uq_snapshots_backup_job",
        "snapshots",
        ["backup_job_id"],
        unique=True,
    )
    op.create_index(
        "ix_snapshots_device_captured",
        "snapshots",
        ["device_id", sa.text("captured_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_snapshots_config_object",
        "snapshots",
        ["config_object_id"],
        unique=False,
    )
    op.create_index(
        "ix_snapshots_retained",
        "snapshots",
        ["is_retained"],
        unique=False,
    )

    op.create_index(
        "ix_retention_marks_type",
        "snapshot_retention_marks",
        ["mark_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_retention_marks_type", table_name="snapshot_retention_marks")

    op.drop_index("ix_snapshots_retained", table_name="snapshots")
    op.drop_index("ix_snapshots_config_object", table_name="snapshots")
    op.drop_index("ix_snapshots_device_captured", table_name="snapshots")
    op.drop_index("uq_snapshots_backup_job", table_name="snapshots")

    op.drop_index("ix_config_objects_storage_status", table_name="config_objects")
    op.drop_index("uq_config_object_s3_key", table_name="config_objects")
    op.drop_index("uq_config_object_content", table_name="config_objects")

    op.drop_index("ix_backup_jobs_device_success", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_scheduled_for", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_created", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_state", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_device_created", table_name="backup_jobs")

    op.drop_index("ix_device_backup_settings_next_run", table_name="device_backup_settings")
    op.drop_index("uq_enabled_daily_time", table_name="device_backup_settings")

    op.drop_index("ix_devices_hostname", table_name="devices")
    op.drop_index("ix_devices_availability_status", table_name="devices")
    op.drop_index("ix_devices_source_present", table_name="devices")
    op.drop_index("uq_devices_zabbix_host_id", table_name="devices")

    op.drop_index("ix_users_active_role", table_name="users")
    op.drop_index("uq_users_username", table_name="users")
