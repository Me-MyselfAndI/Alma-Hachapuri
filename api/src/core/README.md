# Core (shared — not an entity domain)

| Path | Slice | Spec |
|------|-------|------|
| `config.py` | — | Env settings (existing) |
| `database.py` | Database foundation | Engine, Session, Base, `get_db` |
| `permissions.py` | Permissions | Role enum, ROLE_PERMISSIONS |
| `deps.py` | Permissions | `get_current_account`, `require_permission` |
| `security.py` | Account & login | JWT + password helpers (used by account domain) |

Role and permission **docs:** [docs/entities/role.md](../../../docs/entities/role.md), [permission.md](../../../docs/entities/permission.md)
