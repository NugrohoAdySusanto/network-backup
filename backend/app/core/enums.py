from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"


class AvailabilityStatus(StrEnum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class RetentionPolicy(StrEnum):
    STANDARD_31 = "standard_31"
    SMART_7_4_12_3 = "smart_7_4_12_3"


class TriggerType(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class BackupJobState(StrEnum):
    QUEUED = "QUEUED"
    PRECHECKING_ZABBIX = "PRECHECKING_ZABBIX"
    CONNECTING = "CONNECTING"
    COLLECTING = "COLLECTING"
    NORMALIZING = "NORMALIZING"
    VALIDATING = "VALIDATING"
    HASHING = "HASHING"
    UPLOADING = "UPLOADING"
    VERIFYING = "VERIFYING"
    RETRYING = "RETRYING"
    SUCCESS_CHANGED = "SUCCESS_CHANGED"
    SUCCESS_NO_CHANGE = "SUCCESS_NO_CHANGE"
    SKIPPED_DEVICE_DOWN = "SKIPPED_DEVICE_DOWN"
    SKIPPED_STATUS_UNKNOWN = "SKIPPED_STATUS_UNKNOWN"
    FAILED = "FAILED"


class ChangeStatus(StrEnum):
    BASELINE = "baseline"
    CHANGED = "changed"
    NO_CHANGE = "no_change"


class StorageStatus(StrEnum):
    AVAILABLE = "available"
    DELETED = "deleted"
    ERROR = "error"


class RetentionMarkType(StrEnum):
    STANDARD_WINDOW = "STANDARD_WINDOW"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"
    LATEST_GOOD = "LATEST_GOOD"
