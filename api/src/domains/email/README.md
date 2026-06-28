# Domain: Email notification

**Slice:** Email · **Doc:** [docs/entities/email-notification.md](../../../docs/entities/email-notification.md)

## Files

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy `EmailNotification` (+ `conversation_id`) |
| `schemas.py` | EmailNotificationRead, EmailSendRequest, EmailTemplateInfo |
| `service.py` | EmailService (S7a, S7), SMTP adapter, templates |
| `preconditions.py` | E3 retry gate, conversation resolution (F2.6 tests) |
| `router.py` | E1–E4, E6; lead-scoped L6 + E2 |

## Router mounts (in `src/main.py`)

| Prefix | Routes |
|--------|--------|
| `/api/v1/emails` | E1, E3, E4, E6 |
| `/api/v1/leads/{lead_id}/emails` | L6, E2 |

## Depends on

Lead domain (FK)

## Consumed by

L1a via S7a (`send_verification_email`); L1b via S7 (`send_lead_created_notifications`)
