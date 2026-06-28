"""Domain modules — one package per entity.

Importing this package re-exports every ORM model so that
``src.core.database.Base.metadata`` is fully populated. Alembic's ``env.py``
relies on this single import to discover all tables; application code that
needs ``Base.metadata`` should also import ``src.domains``.

We chose this single side-effect import over a separate ``src/models.py``
module because each model already lives next to the rest of its domain
package — keeping imports here avoids a second source of truth.
"""

from src.domains.account.models import Account
from src.domains.email.models import EmailNotification
from src.domains.lead.models import Lead, LeadIntakePending
from src.domains.prospect.models import Prospect
from src.domains.resume_file.models import ResumeFile
from src.domains.state_history.models import LeadStateHistory

__all__ = [
    "Account",
    "EmailNotification",
    "Lead",
    "LeadIntakePending",
    "LeadStateHistory",
    "Prospect",
    "ResumeFile",
]
