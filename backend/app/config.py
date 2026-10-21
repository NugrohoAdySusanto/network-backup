from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Network Backup Dashboard"
    app_env: str = "development"
    app_timezone: str = "Asia/Jakarta"
    app_secret: str

    database_url: str
    redis_url: str = "redis://redis:6379/0"
    session_redis_url: str = "redis://redis:6379/1"

    session_ttl_seconds: int = 600
    remember_session_ttl_seconds: int = 600
    cookie_secure: bool = False
    session_cookie_name: str = "nb_session"

    password_min_length: int = 8
    password_max_length: int = 128

    bootstrap_users_enabled: bool = False
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = ""
    bootstrap_viewer_username: str = "viewer"
    bootstrap_viewer_password: str = ""

    zabbix_url: str = ""
    zabbix_api_token: str = ""
    zabbix_network_group_id: str = ""
    zabbix_availability_item_key: str = "icmpping"
    zabbix_sync_interval_seconds: int = 30
    zabbix_availability_max_age_seconds: int = 120

    network_ssh_username: str = ""
    network_ssh_password: str = ""
    network_ssh_enable_password: str = ""
    network_ssh_port: int = 22
    ssh_connect_timeout_seconds: int = 15
    ssh_command_timeout_seconds: int = 60
    ssh_strict_host_key_checking: bool = False
    ssh_known_hosts_path: str = "/app/known_hosts"

    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_secure: bool = True

    ceph_health_url: str = ""
    ceph_health_token: str = ""
    ceph_health_username: str = ""
    ceph_health_password: str = ""
    ceph_health_pinned_fingerprint: str | None = None
    ceph_health_interval_seconds: int = 30

    feishu_webhook_url: str = ""

    smtp_host: str = "smtp.feishu.cn"
    smtp_port: int = 465
    smtp_user: str = "no-reply@makuku.co.id"
    smtp_password: str = "E2ivs1dAT9FcdSfK"
    smtp_use_ssl: bool = True
    smtp_from_email: str = "no-reply@makuku.co.id"
    smtp_timeout_seconds: int = 10
    app_base_url: str = "http://localhost:8081"

    backup_max_attempts: int = 3
    backup_retry_delays_seconds: str = "30,120,300"
    backup_worker_concurrency: int = 3
    backup_lock_ttl_seconds: int = 900
    enable_mock_driver: bool = False

    schedule_dispatch_interval_seconds: int = 60
    schedule_slot_minutes: int = 5
    retention_run_hour: int = 2
    retention_purge_grace_hours: int = 24

    log_level: str = "INFO"
    @model_validator(mode="after")
    def adjust_security_defaults(self) -> "Settings":
        if self.app_env.lower() in ("production", "prod") and "cookie_secure" not in self.model_fields_set:
            self.cookie_secure = True
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
