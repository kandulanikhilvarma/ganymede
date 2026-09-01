"""Frozen data contracts for Ganymede.

Several invariants live here at the type level rather than as runtime checks,
because a schema that cannot express a bad state is stronger than a test that
catches one:

  I2  — every Decision carries an experiment Arm (non-optional)
  I3  — every Decision carries the acting policy's propensity (non-optional)
  I8  — ContactEvent is channel-agnostic (Channel enum, no voice assumption)
  I10 — DO_NOT_CONTACT is a first-class Action, not the absence of one
  I13 — a data source declares whether it has calendar dates

Frozen: field changes ripple through every component. Bump the schema version
and update docs/defects.md rather than editing silently.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class Channel(str, Enum):
    VOICE = "voice"
    EMAIL = "email"
    SMS = "sms"
    CHAT = "chat"
    IN_APP = "in_app"


class Action(str, Enum):
    # I10: not contacting is a decision with money attached, not a null.
    DO_NOT_CONTACT = "do_not_contact"
    REMINDER = "reminder"
    PLAN_OFFER = "plan_offer"
    RESTRUCTURE = "restructure"
    SETTLEMENT = "settlement"
    ESCALATE = "escalate"


class Arm(str, Enum):
    # I2: full risk+coaching, queue-only, and a permanent no-treatment control.
    FULL = "full"
    RISK_ONLY = "risk_only"
    CONTROL = "control"


class DelinquencyState(str, Enum):
    CURRENT = "current"
    DRIFTING = "drifting"
    DELINQUENT = "delinquent"
    IN_TREATMENT = "in_treatment"
    PROMISE_OPEN = "promise_open"
    CURED = "cured"
    CHARGED_OFF = "charged_off"


class Capacity(str, Enum):
    CAN_PAY = "can_pay"
    CANNOT_PAY = "cannot_pay"
    UNKNOWN = "unknown"


class Willingness(str, Enum):
    WILL_PAY = "will_pay"
    WILL_NOT_PAY = "will_not_pay"
    UNKNOWN = "unknown"


class PromiseStatus(str, Enum):
    KEPT = "kept"
    BROKEN = "broken"
    PARTIAL = "partial"
    NONE = "none"


class DataSource(BaseModel):
    """A dataset feeding the panel. I13: timing features may only read a source
    whose has_calendar_dates is True."""

    name: str
    has_calendar_dates: bool
    is_synthetic: bool = False


class BorrowerState(BaseModel):
    """Capacity x willingness (I7). confidence gates whether Coach Lens branches
    on a strategy or falls back to a diagnostic question."""

    capacity: Capacity
    willingness: Willingness
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def is_certain(self) -> bool:
        return (
            self.capacity is not Capacity.UNKNOWN
            and self.willingness is not Willingness.UNKNOWN
            and self.confidence >= 0.6
        )


class ContactEvent(BaseModel):
    """I8: channel-agnostic. A voice call and an email are the same shape."""

    borrower_id: str
    channel: Channel
    ts: datetime
    reached: bool
    transcript: str | None = None


class Score(BaseModel):
    """A model output with the reason codes an agent needs to trust it."""

    borrower_id: str
    model_version: str
    probability: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list, max_length=5)


class Hint(BaseModel):
    """I5: a strategy hint carries its support count so thin evidence is visible.
    I11: hints are rate-limited upstream; this is the record of one shown."""

    text: str
    is_deterministic: bool
    support_count: int | None = None  # None only for deterministic/compliance hints

    @model_validator(mode="after")
    def _strategy_hints_show_support(self) -> "Hint":
        if not self.is_deterministic and self.support_count is None:
            raise ValueError("I5: a strategy hint must carry a support_count")
        return self


class Promise(BaseModel):
    """PTP extracted from a conversation. Specificity is the coaching target."""

    borrower_id: str
    amount: float | None = None
    due: date | None = None
    method: str | None = None
    extractor_confidence: float = Field(ge=0.0, le=1.0)

    @property
    def is_specific(self) -> bool:
        return self.amount is not None and self.due is not None and self.method is not None


class Outcome(BaseModel):
    borrower_id: str
    promise_status: PromiseStatus
    recovered: float
    resolved_on: date


class Decision(BaseModel):
    """The append-only log row. Everything trains on this table, and I2/I3 make
    the two fields that make it trainable non-optional."""

    borrower_id: str
    ts: datetime
    action: Action
    arm: Arm  # I2
    propensity: float = Field(ge=0.0, le=1.0)  # I3: for IPW and off-policy eval
    score: Score | None = None
    hint_shown: Hint | None = None
    agent_action: Action | None = None
    override_reason: str | None = None

    @model_validator(mode="after")
    def _override_needs_reason(self) -> "Decision":
        if (
            self.agent_action is not None
            and self.agent_action is not self.action
            and not self.override_reason
        ):
            raise ValueError("an override must carry a reason")
        return self
