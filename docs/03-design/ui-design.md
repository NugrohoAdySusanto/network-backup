# Network Backup Dashboard — Final Design System & UI/UX Specification

**Version:** 1.0  
**Status:** Visual Scope Frozen for v1  
**Basis:** Existing `mockup.html`, previous `DESIGN.md`, reviewed video mockup, and finalized functional decisions.

---

# 1. Design Philosophy

The application retains the existing **Enterprise Network Operations Center (NOC)** visual direction.

Primary characteristics:

- high technical readability;
- compact but not crowded data presentation;
- clear status hierarchy;
- strong Light / Dark Mode parity;
- subdued enterprise palette;
- monospace accents for infrastructure data;
- responsive horizontal device table;
- modal-based secondary workflows;
- minimal page navigation in v1.

The current mockup remains the visual reference; v1 changes focus on replacing demo behavior/data with real backend-driven behavior.

---

# 2. Visual Identity

## 2.1 Typography

### DM Sans

Used for:

- page headings;
- body;
- buttons;
- table content;
- modal titles/forms.

### Space Mono

Used for:

- IP addresses;
- eyebrow labels;
- SHA-256 values;
- timestamps;
- retention badges;
- configuration filenames;
- technical status values.

---

# 3. Color System

The current CSS-variable-based design system is retained.

## 3.1 Core Light Mode

```text
Page Background : #f5f7f8
Surface         : #ffffff
Soft Surface    : #eef3f5
Primary Ink     : #142b39
Secondary Ink   : #3b5262
Muted           : #647784
Border          : #dfe7ea
Accent          : #123c53
Focus           : #2897bd
Success         : #168453
Danger          : #c84040
Amber           : #b45309
```

## 3.2 Core Dark Mode

```text
Page Background : #0d171d
Surface         : #16242e
Soft Surface    : #203340
Primary Ink     : #f1f6f8
Secondary Ink   : #c0d3de
Muted           : #8ea2af
Border          : #2a3f4e
Accent          : #38bdf8
Focus           : #38bdf8
Success         : #22c55e
Danger          : #f87171
Amber           : #fbbf24
```

---

# 4. Status Color Semantics

## Device

```text
Active     -> Green
Non-Active -> Red
```

## Backup Result

```text
Success       -> Green
Running       -> Blue/Sky
Queued        -> Neutral/Slate
Retrying      -> Amber
Failed        -> Red
```

## Change Detection

```text
No Change -> Neutral/Slate or Green-subtle
Changed   -> Amber
```

`Changed` is not an error; it must not use destructive red styling.

## Ceph Health

```text
HEALTH_OK   -> Green
HEALTH_WARN -> Amber
HEALTH_ERR  -> Red
```

---

# 5. Main Layout

Retain:

```text
+------------------------------------------------------------------+
| HEADER                                                           |
| Title   Total Devices | Backup Success | Ceph Health | User | ◐  |
+------------------------------------------------------------------+
| DEVICE LIST                                                      |
| Supporting text                                                  |
+------------------------------------------------------------------+
| DEVICE TABLE                                                     |
| Host | Status | IP | Model | Driver | Backup | Last | Change ... |
+------------------------------------------------------------------+
| Inline status / toast feedback                                   |
+------------------------------------------------------------------+
| FOOTER                                                           |
+------------------------------------------------------------------+
```

Maximum width remains approximately:

```text
1500px
```

The table remains horizontally scrollable for smaller screens.

---

# 6. Login Modal

Retain the current visual language:

- centered modal;
- blurred backdrop;
- Network Backup Portal title;
- Username;
- Password;
- Show/Hide Password;
- Remember Session;
- Quick Autofill;
- Theme Toggle;
- primary Sign In action.

Functional changes:

- authentication is backend-driven;
- role terminology displayed as `Admin` / `Viewer`;
- no localStorage user database as the authoritative account store.

The current default-account / Quick Autofill UI is retained.

---

# 7. Header

## 7.1 Left Side

```text
OPERATIONS / NETWORK
Network Backup
```

Retain current typography and spacing.

## 7.2 KPI Cards

### Total Devices

Example:

```text
Total Devices
24 devices
```

### Backup Success Today

Replace mockup wording:

```text
Backups Completed
```

with:

```text
Backup Success Today
96%
```

Optional secondary text may show:

```text
23 / 24
```

if space remains visually balanced.

### Ceph Health

Replace generic:

```text
S3 Status
OK
```

with real:

```text
Ceph Health
HEALTH_OK
```

Health pill/dot changes color based on actual state.

## 7.3 Account

Display:

```text
Admin (username)
Viewer (username)
```

Account dropdown contains:

- Manage account preferences
- Logout

Replace `End demo session` wording with normal `Logout`.

## 7.4 Theme

Retain Dark / Light toggle.

---

# 8. Device List Header

Retain:

```text
Device list
```

Change subtitle from demo language to production wording, for example:

```text
Monitor device backup status and manage centralized configuration backups.
```

Remove:

```text
DEMO DASHBOARD
```

v1 does not include Export CSV / Export PDF buttons.

These may return in v2.

---

# 9. Device Table

Final minimum columns:

```text
HOSTNAME
STATUS
IP ADDRESS
MODEL
BACKUP DRIVER
BACKUP
LAST BACKUP
CHANGE
DOWNLOAD
ACTIONS
```

## 9.1 Hostname Cell

Retain current layout:

```text
Hostname                         Retention Badge
```

Badge:

```text
31 Days
Smart Ret.
```

## 9.2 Status

Read-only Zabbix-driven pill:

```text
Active
Non-Active
```

No user toggle.

## 9.3 IP Address

Use Space Mono.

## 9.4 Model

Real environment only:

- Sangfor
- Mikrotik
- Ruijie

No Cisco demo models in production dataset.

## 9.5 Backup Driver

Keep dropdown visual pattern, but values become real Driver Registry entries.

Example:

```text
Sangfor NSF Driver
Mikrotik RouterOS Driver
Ruijie Switch Driver
Ruijie AP Driver
```

Viewer sees a read-only value instead of an editable select.

## 9.6 Backup

Admin menu:

```text
Backup Now
Schedule
```

Viewer:

- action hidden or disabled;
- no operational execution.

## 9.7 Last Backup

Show latest successful backup timestamp.

If scheduled:

```text
Daily at 01:00
```

may appear as amber secondary text.

## 9.8 Change

New v1 column.

Badge:

```text
Changed
No Change
—
```

`—` is used before first comparable successful backup.

## 9.9 Download

Admin:

- button visible when retained snapshot exists.

Viewer:

- no download button;
- show `Restricted` or `—` depending final visual preference.

Recommended: use `Restricted` subtle badge to make permission behavior explicit.

## 9.10 Actions

Admin:

```text
Save
Clear
```

Viewer:

- hidden/disabled.

Save persists:

- driver;
- daily schedule;
- retention.

Clear removes:

- driver assignment;
- schedule.

Clear does not delete history or stored backups.

---

# 10. Schedule Modal

Replace current one-time datetime behavior.

Final v1 fields:

```text
Device
Daily Backup Time
Retention Policy
```

Retention:

```text
31 Days Retention
Smart Retention
```

Smart tooltip:

```text
Daily   7
Weekly  4
Monthly 12
Yearly  3
```

Remove text:

```text
Backups will only execute while this browser page remains open.
```

Replace with:

```text
The schedule is stored on the server and runs automatically every day.
```

Buttons remain:

```text
Cancel
Create / Save Schedule
```

---

# 11. Backup Progress Feedback

The current inline `aria-live` notice area is retained.

Examples:

```text
Backup job queued for MKK-Core-Switch.
Connecting to device...
Configuration collected successfully.
No configuration change detected.
New configuration version stored successfully.
Backup failed after 3 attempts.
```

Long-running operations should not lock the page.

---

# 12. Backup Archive Modal

The existing large modal structure remains useful.

Final title:

```text
Backup Archives — <hostname>
```

Header info:

- IP;
- Model;
- Driver;
- Device status;
- Active retention policy.

## 12.1 Archive Source

Remove synthetic archive generation.

Rows come from real database snapshot metadata.

## 12.2 Columns

Recommended:

```text
DATE & TIME
RETENTION TYPE
FILENAME / SNAPSHOT
FILE SIZE
SHA-256
CHANGE
OBJECT STATUS
ACTION
```

If horizontal space becomes excessive, SHA can be shortened in the list:

```text
8f1d...e9a2
```

with full 64-character digest available via tooltip/copy/detail.

## 12.3 Integrity Wording

Do not use `Verified ✓` to imply HMAC validation in v1.

Use:

```text
Checksum OK
Object Verified
```

where appropriate.

## 12.4 Download

Admin only.

Viewer may open the history modal but cannot download.

## 12.5 Retention Tabs

The current policy tabs can remain:

```text
31 Days Retention
Smart Retention
```

They must show actual retained snapshots rather than generated synthetic files.

## 12.6 Manifest Download

Remove from v1 unless later reintroduced as reporting.

It belongs more naturally with v2 reporting.

---

# 13. Account Preferences Modal

Retain current visual structure.

## 13.1 Change Password

Retain:

- Old Password
- New Password
- Confirm Password

## 13.2 User Management

Admin only.

Role options become:

```text
Admin
Viewer
```

Retain protections:

- cannot delete current logged-in account;
- cannot remove the last Admin.

## 13.3 Persistence Text

Remove browser-localStorage wording.

Replace:

```text
Credential changes are saved securely by the application.
```

Exact backend security wording will be finalized after authentication design.

---

# 14. Retention Badge

### Standard

```text
31 Days
```

Suggested color:

- Sky / Blue.

### Smart

```text
Smart Ret.
```

Suggested color:

- Purple.

Retain current aligned badge placement.

---

# 15. Ceph Health Visual

Header must map:

```text
HEALTH_OK
HEALTH_WARN
HEALTH_ERR
```

Visual:

```text
HEALTH_OK   -> green pulse dot
HEALTH_WARN -> amber pulse dot
HEALTH_ERR  -> red pulse dot
```

Tooltip may contain last health refresh time.

---

# 16. Light / Dark Mode

Retain current full inversion.

Dark mode must continue to cover:

- page background;
- cards;
- table;
- dropdown;
- modals;
- input fields;
- badges;
- status pills;
- tooltips.

Theme preference may remain browser-local because it is UI preference, not operational data.

---

# 17. Accessibility

Retain current good mockup behavior:

- `aria-live` operational feedback;
- keyboard focus outlines;
- Escape closes modal;
- outside click closes dropdown;
- backdrop click closes modal where appropriate;
- labels associated with inputs;
- visible focus state.

---

# 18. Responsive Behavior

## Desktop

Primary design target.

## Tablet / Small Desktop

- header cards wrap;
- table scrolls horizontally;
- modal remains centered.

## Mobile

Functional but not a primary operational target.

Do not redesign the application into stacked mobile cards for v1.

---

# 19. Removed Demo Visuals / Text

Remove or replace:

```text
DEMO DASHBOARD
Network Backup Dashboard — Simulation
Demo session only
Generated dummy archive references
Cisco demo models
Browser-tab schedule warning
End demo session
Export CSV
Export PDF
Manifest download
```

---

# 20. v2 Visual Capabilities & Scope Finalization

## Security & Cryptographic Capabilities (Delivered)

```text
zlib Deflate (Level 6, 'NBZ1' Magic Header) Transparent Compression
AES-256-CBC Payload Encryption & PKCS#7 Padding
HMAC-SHA256 Authenticated Envelope (Encrypt-then-MAC, 32B tag)
Database Credential Vault Upgraded to 256-bit (AES-256-CBC + HMAC-SHA256)
Active Storage Repository Indicator & Encrypted S3 Manifest Protection
Interactive Cryptography Visualizer & SubtleCrypto Live Lab (/crypto-animation.html)
Quick-Access 'Animasi Kriptografi' Header Button & Account Dropdown Menu Entry
Strategic Roadmap: Infisical KMS evaluated as future secret management architecture
```

## Reporting (Delivered)

```text
Export Excel (.xlsx) with styled sheets and KPI cards
Export PDF (.pdf) with executive summary tables
Date Range Filter & KPI Summary Cards
```

## Excluded Scope

Per user design requirements, cross-version visual diff, configuration drift badges, and drift audit modals were removed from the interface layout to maintain an uncluttered and efficient dashboard.
