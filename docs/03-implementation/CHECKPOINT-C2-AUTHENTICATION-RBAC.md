# Checkpoint C2 — Authentication + RBAC

**Status:** Implementation baseline created  
**Depends on:** C1 PostgreSQL schema  
**Contract:** `API-CONTRACT-v1.0.md`

## Scope

C2 implements:

```text
Argon2id password hashing
server-side Redis sessions
Secure/HttpOnly session cookie support
Remember Me TTL
CSRF token validation
Admin / Viewer RBAC
login / logout / me
change own password
Admin user list/create/deactivate
soft user deletion
bootstrap-user CLI
standardized application error responses
request-id response header
```

C2 deliberately does NOT implement:

```text
frontend login integration
Quick Autofill integration
Zabbix
device APIs
backup execution
Ceph
Feishu
```

Those remain later checkpoints.

---

# 1. Endpoints Added

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/change-password

GET    /api/v1/users
POST   /api/v1/users
DELETE /api/v1/users/{user_id}
```

## RBAC

```text
Admin:
  user management + normal authenticated access

Viewer:
  normal authenticated access
  NO user management
```

Backend enforcement is independent from frontend button visibility.

---

# 2. Session Design

Browser receives only:

```text
nb_session=<opaque random session id>
```

Session contents are held in Redis DB 1:

```text
user_id
csrf_token
remember_me
created_at
```

Cookie target attributes:

```text
HttpOnly
SameSite=Lax
Secure=true in HTTPS production
```

No JWT is stored in localStorage.

---

# 3. CSRF

Login does not require CSRF.

After login/backend session restore, frontend receives:

```text
csrf_token
```

State-changing authenticated requests send:

```http
X-CSRF-Token: <token>
```

Required for:

```text
logout
change password
create/deactivate users
future backup settings
future Backup Now
```

---

# 4. Password Storage

Database stores only:

```text
$argon2id$...
```

Password policy is configurable:

```text
PASSWORD_MIN_LENGTH=8
PASSWORD_MAX_LENGTH=128
```

---

# 5. Bootstrap Users

Do not seed plaintext/default passwords in Alembic migrations.

Configure development/demo values in `.env`:

```text
BOOTSTRAP_USERS_ENABLED=true
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=<choose password>
BOOTSTRAP_VIEWER_USERNAME=viewer
BOOTSTRAP_VIEWER_PASSWORD=<choose password>
```

Then run once:

```bash
docker compose run --rm api python -m app.cli.bootstrap_users
```

The command:

```text
hashes passwords with Argon2id
skips existing usernames
does not overwrite existing passwords
```

Production should normally set:

```text
BOOTSTRAP_USERS_ENABLED=false
```

---

# 6. User Delete Semantics

API:

```text
DELETE /api/v1/users/{id}
```

Database behavior:

```text
is_active = false
```

It is a soft deactivation.

Rules:

```text
cannot deactivate current logged-in account
cannot deactivate last active Admin
historical foreign keys remain intact
```

---

# 7. Validation Procedure

First verify C1 on disposable PostgreSQL:

```bash
cp .env.example .env
# configure required values

docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
```

Enable and create bootstrap accounts:

```bash
docker compose run --rm api python -m app.cli.bootstrap_users
```

Start full scaffold:

```bash
docker compose up -d --build
```

## Login

```bash
curl -i       -c cookies.txt       -H 'Content-Type: application/json'       -d '{"username":"admin","password":"<password>","remember_me":false}'       http://localhost:8080/api/v1/auth/login
```

Save the returned `csrf_token`.

## Me

```bash
curl -b cookies.txt       http://localhost:8080/api/v1/auth/me
```

## List Users

```bash
curl -b cookies.txt       http://localhost:8080/api/v1/users
```

## Create User

```bash
curl -b cookies.txt       -H 'Content-Type: application/json'       -H 'X-CSRF-Token: <csrf-token>'       -d '{"username":"test.viewer","password":"ExamplePass123!","role":"viewer"}'       http://localhost:8080/api/v1/users
```

## Logout

```bash
curl -i       -b cookies.txt       -H 'X-CSRF-Token: <csrf-token>'       -X POST       http://localhost:8080/api/v1/auth/logout
```

---

# 8. C2 Acceptance Gate

C2 is VERIFIED only if:

1. C1 migrations apply successfully;
2. Redis is reachable;
3. bootstrap Admin and Viewer are stored as Argon2id hashes;
4. correct login creates Redis session and HttpOnly cookie;
5. incorrect login returns `INVALID_CREDENTIALS`;
6. `/auth/me` rejects missing/expired sessions;
7. authenticated writes reject missing/wrong CSRF;
8. Viewer receives 403 on `/users`;
9. Admin can list and create users;
10. username is normalized to lower-case;
11. duplicate username is rejected;
12. Admin cannot deactivate self;
13. last active Admin cannot be deactivated;
14. deactivated account cannot authenticate/use existing session;
15. password change verifies current password;
16. unit tests pass;
17. credentials/password hashes never appear in API responses.

---

# 9. Agentic AI Rule

An AI coding agent may begin from C0/C1/C2 **now**.

Its first task must be verification, not redesign:

```text
1. inspect authoritative docs;
2. run Docker/PostgreSQL/Redis;
3. run migrations;
4. run tests;
5. exercise the C2 HTTP flow;
6. fix implementation defects only;
7. report any architecture/schema conflict before changing contracts.
```

Do not let the agent skip directly to Zabbix/SSH until C2 passes its gate.
