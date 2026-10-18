# Network Backup Dashboard — Backup Driver Contract

**Version:** 1.0  
**Status:** Implementation Contract for Backend v1  
**Language:** Python 3.12  
**Primary Transport:** SSH  
**Primary Library:** Netmiko  
**Architecture Pattern:** Driver Registry / Adapter  
**Driver Assignment:** Manual from Web UI  
**Authoritative Orchestrator:** `BackupService`

---

# 1. Purpose

A Backup Driver encapsulates only the vendor/device-specific logic required to:

```text
connect
collect configuration
normalize configuration
validate configuration
cleanup
```

The driver makes Sangfor, Mikrotik, and Ruijie appear identical to the core `BackupService`.

The core application must never contain a vendor-selection chain such as:

```python
if vendor == "mikrotik":
    ...
elif vendor == "sangfor":
    ...
elif vendor == "ruijie":
    ...
```

The only dispatch mechanism is the Driver Registry:

```text
driver_key
   |
   v
DriverRegistry
   |
   v
BackupDriver implementation
```

---

# 2. Mandatory Boundary

A driver **owns**:

```text
SSH connection behavior
vendor-specific read-only commands
configuration collection
vendor-specific normalization
vendor-specific validation
output extension/metadata
```

A driver must **not own**:

```text
Zabbix queries
PostgreSQL writes
Celery scheduling
Redis locks
SHA comparison business decision
Ceph S3 upload/download
retention
snapshot creation
Feishu notification
user authentication/RBAC
frontend logic
```

This boundary is mandatory.

---

# 3. Initial Driver Registry

v1 starts with:

```text
sangfor-nsf
mikrotik-routeros
ruijie-switch
ruijie-ap
```

Manual web assignment:

```text
Device -> Backup Driver dropdown -> driver_key
```

The frontend sees the stable `driver_key`, never a Python class path.

---

# 4. Netmiko-First Rule

All v1 drivers should use Netmiko if the real device can be reliably handled with it.

Architecture:

```text
SangforNSFDriver --------\
MikrotikRouterOSDriver ---+--> Netmiko / SSH
RuijieSwitchDriver -------/
```

If one specific vendor/device cannot be handled reliably by Netmiko:

```text
BackupDriver public contract
        |
        v
Vendor Driver
        |
        +-- Netmiko when possible
        |
        +-- private custom Python SSH implementation if necessary
```

The fallback must remain **inside that driver package/module**.

Do not modify:

```text
BackupService
API
Database schema
S3 Service
Scheduler
```

just because one driver requires a different SSH implementation.

Prefer an imported Python implementation over spawning an external script/process. If an external script is absolutely required, wrap it behind the same driver contract and return the same typed results/exceptions.

---

# 5. Driver Metadata Contract

Each driver exposes static metadata.

Conceptual model:

```python
@dataclass(frozen=True)
class DriverMetadata:
    key: str
    label: str
    transport: str
    implementation: str
    output_extension: str
    vendor_hint: str | None = None
    model_hint: str | None = None
```

Example registry metadata:

```python
DriverMetadata(
    key="ruijie-switch",
    label="Ruijie Switch Driver",
    transport="ssh",
    implementation="netmiko",
    output_extension="cfg",
    vendor_hint="Ruijie",
)
```

`vendor_hint` is informational.

Assignment remains manual; it must not silently auto-assign a driver.

---

# 6. Driver Input Context

The driver must not read `.env` directly.

`BackupService` / a connection factory passes the required connection context.

Conceptual model:

```python
@dataclass(frozen=True, repr=False)
class DeviceConnectionContext:
    device_id: int
    hostname: str
    host: str
    port: int
    username: str
    password: str
    connect_timeout: int
    command_timeout: int
```

Sensitive fields must never be included in `repr`, logs, exceptions, or API responses.

The shared read-only network service account is loaded by the backend configuration layer, not by the driver itself.

---

# 7. Collected Configuration Contract

Driver returns configuration content plus non-sensitive metadata.

Conceptual model:

```python
@dataclass(frozen=True)
class CollectedConfig:
    text: str
    extension: str
    encoding: str = "utf-8"
```

The driver must not inject application metadata into the configuration text.

Do not prepend lines such as:

```text
Backup Job ID
Application Timestamp
Retention Policy
S3 Status
SHA-256
Zabbix Status
```

because they would create false configuration changes.

Application metadata belongs in PostgreSQL.

---

# 8. Concrete Base Contract

Recommended abstract contract:

```python
from abc import ABC, abstractmethod


class BackupDriver(ABC):
    metadata: DriverMetadata

    @abstractmethod
    def connect(self, context: DeviceConnectionContext) -> None:
        # Open the read-only device session.
        raise NotImplementedError

    @abstractmethod
    def collect_config(self) -> CollectedConfig:
        # Collect current config using fixed read-only command(s).
        raise NotImplementedError

    @abstractmethod
    def normalize_config(
        self,
        collected: CollectedConfig,
    ) -> str:
        # Remove only known volatile/non-semantic export content.
        raise NotImplementedError

    @abstractmethod
    def validate_config(
        self,
        collected: CollectedConfig,
        normalized_text: str,
    ) -> None:
        # Raise DriverValidationError when config is unacceptable.
        raise NotImplementedError

    @abstractmethod
    def cleanup(self) -> None:
        # Close session/resources. Must be safe to call repeatedly.
        raise NotImplementedError
```

`validate_config()` returns normally on success and raises a typed exception on failure.

This keeps the orchestrator simple.

---

# 9. Driver Lifecycle

The Backup Service owns lifecycle ordering:

```text
1. registry.get(driver_key)
2. driver.connect(context)
3. collected = driver.collect_config()
4. normalized = driver.normalize_config(collected)
5. driver.validate_config(collected, normalized)
6. return collected + normalized to BackupService
7. cleanup in finally block
```

Equivalent pattern:

```python
driver = registry.create(driver_key)

try:
    driver.connect(context)
    collected = driver.collect_config()
    normalized = driver.normalize_config(collected)
    driver.validate_config(collected, normalized)
finally:
    driver.cleanup()
```

The driver does not calculate business-level `Changed/No Change`.

That belongs to `ChangeDetectionService`.

---

# 10. Driver Registry Contract

Recommended registry:

```python
class DriverRegistry:
    def register(self, driver_cls: type[BackupDriver]) -> None:
        ...

    def get(self, key: str) -> type[BackupDriver]:
        ...

    def create(self, key: str) -> BackupDriver:
        ...

    def list_metadata(self) -> list[DriverMetadata]:
        ...
```

Rules:

```text
driver key must be globally unique
duplicate key => application startup error
unknown key => DriverNotFoundError
registry metadata drives GET /api/v1/drivers
```

The registry may be explicit:

```python
registry.register(SangforNSFDriver)
registry.register(MikrotikRouterOSDriver)
registry.register(RuijieSwitchDriver)
```

This explicit approach is preferable to complex runtime plugin discovery for this TA.

---

# 11. No Arbitrary Command Rule

Commands are defined inside the vendor driver source code.

Never accept:

```json
{
  "command": "..."
}
```

from the web/API.

The application is a backup system, not a remote shell.

The read-only network service account provides an additional protection layer.

---

# 12. Vendor Command Rule

Exact backup/export commands are **not defined by this contract**.

They must be determined through:

```text
real-device PoC
vendor documentation
verified read-only testing
```

for the actual Sangfor, Mikrotik, and Ruijie firmware/models.

The implementation agent must **not invent vendor commands**.

For each driver, document the verified command in the driver source/test fixture after PoC.

---

# 13. Connection Factory

To avoid duplicating Netmiko options in every driver, use a shared connection factory/helper.

Conceptual boundary:

```text
Driver
   |
   v
NetmikoConnectionFactory
   |
   v
Netmiko ConnectHandler
```

The connection factory owns common settings such as:

```text
username/password
port
connect timeout
command timeout
SSH host-key policy
session/log safety options
```

The vendor driver provides only the device-type/vendor-specific connection parameters needed by Netmiko.

Do not log sensitive ConnectHandler arguments.

---

# 14. Host-Key Verification

Production should prefer SSH host-key verification using a managed known-hosts policy where supported by the chosen Netmiko/Paramiko configuration.

The exact Netmiko parameters may be finalized during implementation against the installed library version.

The architecture requirement is:

```text
production should not blindly trust unknown SSH host keys
```

If strict verification must temporarily be disabled during early lab development, make it an explicit environment setting and do not silently ship it as the production default.

---

# 15. Collection Rules

`collect_config()` must:

1. run only pre-defined read-only command(s);
2. capture the complete configuration required for backup;
3. disable/handle CLI paging when needed;
4. reject obvious command-error output;
5. avoid write/configuration mode;
6. not save the file locally permanently;
7. return configuration to `BackupService`.

Temporary in-memory or short-lived working data is acceptable.

---

# 16. Raw Configuration Definition

For v1, "raw configuration" means the exact text returned by the verified collection routine before application normalization.

Because Netmiko generally returns text, the application defines raw stored bytes as:

```python
raw_bytes = collected.text.encode(collected.encoding)
```

`object_sha256` is calculated over these exact bytes.

The S3 object must store those same bytes.

---

# 17. Normalization Contract

`normalize_config()` exists only to create a stable representation for change detection.

It may remove known volatile values such as:

```text
export-generation timestamp
dynamic session metadata
vendor-generated non-semantic header line
```

It must not remove real configuration.

Rules:

```text
normalization is vendor-specific
normalization must be deterministic
normalization should be idempotent
normalization must not rewrite configuration semantics
normalization output is not used for device restore
raw configuration remains the stored backup
```

Recommended invariant:

```text
normalize(normalize(x)) == normalize(x)
```

Conceptually, if the method accepts `CollectedConfig`, tests should enforce equivalent idempotent behavior on normalized text.

---

# 18. Line Ending / Whitespace Policy

Do not aggressively normalize arbitrary whitespace because whitespace can be meaningful on some network platforms.

Allowed common normalization only when proven safe for that vendor.

Potential examples:

```text
normalize CRLF/LF consistently
strip a known generated timestamp line
remove known trailing terminal prompt
```

Do not globally:

```text
sort lines
strip indentation
collapse all spaces
remove comments blindly
```

unless verified as non-semantic for that specific driver.

---

# 19. Validation Contract

`validate_config()` protects against false successful backups.

Common validation checks:

```text
collected text exists
raw content is not empty
raw byte length is above a driver-defined minimum
normalized text is not empty
output does not match known CLI/auth/error responses
output contains expected vendor/config structure where safely identifiable
```

Vendor-specific checks belong in each driver.

A successful SSH connection alone is **not** a successful configuration backup.

---

# 20. Validation Result

Prefer typed exceptions instead of booleans.

Good:

```python
driver.validate_config(...)
# returns None on success
# raises DriverValidationError on failure
```

Avoid:

```python
if driver.validate_config(...) == False:
```

Typed exceptions preserve useful failure classification.

---

# 21. Driver Exception Hierarchy

Recommended hierarchy:

```python
class DriverError(Exception):
    code: str
    retryable: bool = False


class DriverNotFoundError(DriverError):
    code = "DRIVER_NOT_FOUND"


class DriverConnectionError(DriverError):
    code = "CONNECTION_ERROR"
    retryable = True


class DriverAuthenticationError(DriverError):
    code = "AUTHENTICATION_FAILED"
    retryable = False


class DriverConnectionTimeoutError(DriverError):
    code = "CONNECTION_TIMEOUT"
    retryable = True


class DriverCommandTimeoutError(DriverError):
    code = "COMMAND_TIMEOUT"
    retryable = True


class DriverCollectionError(DriverError):
    code = "COMMAND_FAILED"


class DriverNormalizationError(DriverError):
    code = "NORMALIZATION_FAILED"


class DriverValidationError(DriverError):
    code = "INVALID_CONFIG"
    retryable = False
```

The concrete implementation may carry a sanitized message and original internal exception chaining.

Do not expose the internal exception directly to the frontend.

---

# 22. Exception-to-Backup-Job Mapping

`BackupService` maps driver exceptions to job metadata.

| Driver Exception | failure_stage | failure_code | Retry |
|---|---|---|:---:|
| `DriverConnectionTimeoutError` | `CONNECTING` | `CONNECTION_TIMEOUT` | Yes |
| `DriverAuthenticationError` | `CONNECTING` | `AUTHENTICATION_FAILED` | No |
| `DriverConnectionError` | `CONNECTING` | `SSH_TRANSPORT_ERROR` | Usually Yes |
| `DriverCommandTimeoutError` | `COLLECTING` | `COMMAND_TIMEOUT` | Yes |
| `DriverCollectionError` | `COLLECTING` | `COMMAND_FAILED` | Depends on cause |
| `DriverNormalizationError` | `NORMALIZING` | `NORMALIZATION_FAILED` | No |
| `DriverValidationError` | `VALIDATING` | `INVALID_CONFIG` | No |

Retry policy is decided by BackupService/Celery, not inside the driver.

The driver may expose `retryable` as classification metadata but must not sleep/retry the whole job itself.

---

# 23. Retry Boundary

Do not implement full-job retries inside:

```text
Sangfor driver
Mikrotik driver
Ruijie driver
```

Celery/BackupService owns retry sequencing:

```text
Attempt 1
   |
failure
   v
RETRYING
   |
Attempt 2
...
```

A driver method may use minimal library-level behavior required for a single SSH operation, but not business-level retry policy.

---

# 24. Zabbix Boundary

The driver never checks device availability through Zabbix.

Correct flow:

```text
BackupService
   |
   +-- ZabbixService fresh pre-check
   |
   +-- if UP:
           Driver.connect()
```

If Zabbix says:

```text
DOWN
UNKNOWN
```

the driver is not invoked.

---

# 25. SHA Boundary

The driver never calculates or stores the business hashes.

Correct flow:

```text
Driver
  |
  +-- raw text
  +-- normalized text
          |
          v
ChangeDetectionService
  |
  +-- content_sha256(normalized)
  +-- object_sha256(raw bytes)
```

`content_sha256` determines:

```text
baseline
changed
no_change
```

`object_sha256` verifies stored raw S3 bytes.

---

# 26. S3 Boundary

Driver does not know:

```text
S3 endpoint
bucket
access key
secret key
object key
retention
snapshot id
```

Correct:

```text
Driver -> returns config
BackupService -> hashes/decision
S3Service -> stores physical object
```

---

# 27. Feishu Boundary

Driver does not send notifications.

Correct:

```text
Driver exception
      |
      v
BackupService/Celery terminal state
      |
      v
NotificationService
      |
      v
Feishu webhook
```

---

# 28. Cleanup Contract

`cleanup()` must:

```text
close SSH connection if open
release driver-local resources
be safe after partial connection failure
be safe to call more than once
not raise a new exception that masks the original failure
```

Recommended use:

```python
try:
    ...
finally:
    try:
        driver.cleanup()
    except Exception:
        logger.warning("Driver cleanup failed")
```

Sanitized log only.

---

# 29. Driver Logging Rules

Allowed fields:

```text
job_id
device_id
hostname
driver_key
state/stage
duration
sanitized error code
```

Never log:

```text
username if unnecessary
password
full connection dictionary
raw secret-bearing config
S3 credential
Zabbix token
```

Do not enable Netmiko session logs containing configuration in production by default.

If session logging is needed for lab debugging, it must be explicitly enabled and protected.

---

# 30. Driver Output Filename

Driver owns only the extension:

```text
rsc
conf
cfg
txt
```

The application/snapshot service generates the display filename.

Example:

```text
mkk-core-switch_20261004_011004.cfg
```

Driver must not generate S3 paths.

---

# 31. Driver Assignment Semantics

Assignment is manual.

Example:

```text
MKK-Firewall
-> sangfor-nsf

MKK-Router
-> mikrotik-routeros

MKK-Core-Switch
-> ruijie-switch
```

The backend may expose `vendor_hint/model_hint` to help the Admin, but it must not silently change the assigned driver when Zabbix inventory changes.

If inventory changes and the current assignment looks suspicious, future UI may show a warning; v1 does not require automatic reassignment.

---

# 32. Wrong Driver Behavior

If an Admin assigns an incompatible driver, the job should fail cleanly through normal driver validation/connection flow.

Recommended failure:

```text
FAILED
failure_stage = CONNECTING or VALIDATING
failure_code = DRIVER_INCOMPATIBLE
```

A driver may perform a safe read-only identity check after connection if the real platform supports it and if needed.

Do not use destructive probing.

---

# 33. Driver Implementation Specifications

### 1. Ruijie Switch Driver (`ruijie-switch`)
- **Key:** `ruijie-switch`
- **Device Type (Netmiko):** `ruijie_os`
- **Export Command:** `show running-config`
- **Output Extension:** `txt`
- **Standard Filename:** `config.txt`
- **Privilege Mode Requirement:**
  Ruijie Switch CLI requires entering enable/privilege mode (`enable`) using privilege secret password (configured via `NETWORK_SSH_ENABLE_PASSWORD` or per-device credential). No default password is used; if unconfigured, backup aborts with `DRIVER_CONFIGURATION_ERROR`.
- **Cryptographic Compatibility:**
  Older Ruijie switch hardware requires enabling legacy Key Exchange algorithms (`diffie-hellman-group14-sha1`, `diffie-hellman-group-exchange-sha1`) and `ssh-rsa` host key algorithm in Paramiko transport.
- **Normalization:**
  Strips dynamic headers `Building configuration...`, `Current configuration : <N> bytes`, and `! Time: ...` to ensure deterministic SHA-256 computation.
- **Verified Target:** Tested and verified on `MKK-HQ_DMZ` (`10.11.10.2:22345`).

### 2. Sangfor NSF Driver (`sangfor-nsf`)
- **Key:** `sangfor-nsf`
- **Output Extension:** `txt`
- **Standard Filename:** `config.txt`
- **Command:** `show running-configuration` (exact command syntax required by Sangfor NSF CLI)
- **Transport & Paging:** Paramiko interactive shell handling `--More--` pagination until prompt `backupadmin# ` is reached.
- **Normalization & Security Behavior:**
  Strips command echo, ANSI control sequences, and prompt artifacts. Validates `config ... end` syntax integrity. Enables line-by-line diff tracking, SHA-256 deduplication, and S3 CAS storage.
- **Verified Target:** Tested and verified live on `MKK-HQ_Firewall` (`10.11.50.1:22345`).

### 3. MikroTik Driver (`mikrotik-routeros`) & Format Architecture: `.rsc` vs `.backup`
- **Format Used by Dashboard:** `.rsc` (`/export compact`)
- **Why `.rsc` Instead of `.backup`:**
  1. **Content Addressable Storage (CAS) Deduplication:** `.rsc` is normalized text script. Computing SHA-256 on normalized `.rsc` enables the system to detect `SUCCESS_NO_CHANGE` vs `SUCCESS_CHANGED`. Binary `.backup` changes timestamp and encryption headers on every execution, making deduplication and diff tracking impossible.
  2. **Audit & Diff Visibility:** NOC engineers and security auditors can perform line-by-line diffs to review configuration changes. `.backup` is a proprietary encrypted binary blob unreadable by text editors.
  3. **Hardware Portability & Partial Restores:** `.rsc` scripts can be edited, audited, and ported across RouterOS hardware models or Cloud Hosted Routers (CHR). `.backup` is tied to specific hardware MAC addresses and RouterOS firmware versions, risking boot failure if restored to different hardware.

The Sangfor and Mikrotik drivers follow the same public shape.

---

# 34. BackupService Consumption Contract

BackupService should be able to use any driver without vendor knowledge.

Conceptual orchestration:

```python
driver = registry.create(settings.driver_key)

try:
    driver.connect(connection_context)

    collected = driver.collect_config()

    normalized = driver.normalize_config(collected)

    driver.validate_config(
        collected=collected,
        normalized_text=normalized,
    )

    raw_bytes = collected.text.encode(collected.encoding)

    content_sha256 = sha256(normalized.encode("utf-8")).hexdigest()
    object_sha256 = sha256(raw_bytes).hexdigest()

    # compare content hash
    # upload/reuse via S3Service
    # create snapshot
    # update backup job

finally:
    driver.cleanup()
```

The real service will update job states between each stage.

---

# 35. State Transition Ownership

Before each driver method, BackupService updates the job state:

```text
connect()          -> CONNECTING
collect_config()   -> COLLECTING
normalize_config() -> NORMALIZING
validate_config()  -> VALIDATING
hashing            -> HASHING
```

Driver does not write state into PostgreSQL itself.

---

# 36. Testing Contract — Unit

Every driver must have unit tests covering:

```text
metadata/key
registry lookup
normalization determinism
normalization idempotence
empty config rejection
known error-output rejection
valid sample acceptance
cleanup safety
sensitive values absent from repr/log message
```

Use sanitized fixtures.

Do not commit real production secrets/configuration if sensitive.

---

# 37. Testing Contract — Integration

Each production driver must be tested against at least one real representative device.

For each driver verify:

```text
SSH connection works using read-only service account
verified command returns complete config
paging does not truncate output
normalization does not remove real settings
validation accepts the real export
repeated backup is stable
connection closes cleanly
no write command is issued
```

Recommended evidence:

```text
>= 10 consecutive successful test collections per driver
```

before considering it stable.

---

# 38. Change-Detection Test

For each vendor driver prepare at least:

```text
Fixture A: config baseline
Fixture B: same config with only volatile timestamp changed
Fixture C: real configuration change
```

Expected:

```text
normalize(A) hash == normalize(B) hash
normalize(A) hash != normalize(C) hash
```

This is particularly important for the TA's SHA-256 Changed / No Change feature.

---

# 39. Driver PoC Checklist

Before coding a real vendor driver fully, record:

```text
Device model
Firmware/version
SSH port
Netmiko device_type that works
Read-only service account tested
Verified collection command
Paging behavior
Expected output extension
Known volatile lines
Known CLI error patterns
Minimum reasonable config size
```

Store this as developer documentation/test notes, not necessarily in the database.

---

# 40. Fallback Custom SSH Checklist

Only use custom Python SSH when Netmiko cannot reliably perform the required read-only collection.

Requirements:

```text
same BackupDriver public methods
same exception hierarchy
same CollectedConfig return shape
same normalization/validation rules
same logging restrictions
same read-only credential
no database/S3/Zabbix/Feishu access
```

Registry metadata changes only:

```text
implementation = "custom_ssh"
```

Frontend/API contract remains unchanged.

---

# 41. Driver Definition of Done

A v1 production driver is complete when:

1. it has a unique stable `driver_key`;
2. it appears through `GET /api/v1/drivers`;
3. Admin can assign it manually;
4. it connects using the read-only account;
5. it runs only verified read-only collection commands;
6. it returns complete configuration;
7. it normalizes only proven volatile content;
8. it rejects empty/invalid output;
9. it raises typed sanitized exceptions;
10. it performs no database/S3/Zabbix/Feishu work;
11. it never exposes credentials in logs;
12. it works with BackupService without vendor-specific conditionals;
13. it passes unit tests;
14. it passes repeated real-device integration testing.

---

# 42. Ruijie AP Driver Specification (`ruijie-ap`)

**Key:** `ruijie-ap`  
**Label:** `Ruijie AP Driver`  
**Target Hardware:** Ruijie Networks APs (e.g. AP850-AR(V3), AP840-I)  
**Port:** 22345  
**Transport:** Netmiko (`device_type: "ruijie_os"`) with legacy `ssh-rsa` host key compatibility (SHA-1 signature enabled in Paramiko)  
**Export Command:** `show running-config`  
**Output Extension:** `.text`  
**Output Filename:** `config.text` (mandatory for Ruijie AP web/CLI restore and import compatibility)  
**Normalization Rules:**
1. Normalize line endings to LF (`\n`).
2. Strip volatile generation header (`^Building configuration\.+`).
3. Strip volatile byte count (`^Current configuration\s*:\s*\d+\s*bytes`).
4. Strip volatile timestamps (`^!\s*Time:\s*.*`).
5. Strip trailing CLI prompt (`\n?[a-zA-Z0-9_\-]+[#>]\s*$`).
6. Strip per-line trailing whitespace and outer blank lines.

**Validation Rules:**
1. Non-empty string.
2. Minimum length >= 50 bytes.
3. Reject output containing CLI error signatures (`invalid input detected`, `% unknown command`, `error: `, `permission denied`).
4. Must contain `hostname` or `version` configuration directives.

