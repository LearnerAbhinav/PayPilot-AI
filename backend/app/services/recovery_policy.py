"""
PayPilot AI — Deterministic Recovery Policy Engine

The AI can RECOMMEND a policy. The backend DECIDES whether a transaction qualifies.
The AI cannot override policy constraints.
"""
from datetime import datetime, timedelta
from typing import NamedTuple


# ─── Policy Configuration ──────────────────────────────────────────────────────

RETRYABLE_FAILURE_CODES = frozenset([
    "upi_timeout",
    "bank_unavailable",
    "network_error",
    "session_expired",
    "try_again",
    "gateway_timeout",
    "connection_reset",
    "server_busy",
])

NON_RETRYABLE_CODES = frozenset([
    "insufficient_funds",
    "card_declined",
    "card_expired",
    "authentication_failed",
    "limit_exceeded",
    "fraud_suspected",
    "account_blocked",
    "invalid_card",
])

# Maximum number of retry attempts allowed per transaction
MAX_RETRY_COUNT = 3

# Only retry transactions up to this amount (risk control)
MAX_RETRYABLE_AMOUNT_INR = 500_000  # 5 lakh

# Minimum transaction amount worth retrying (filter noise)
MIN_RETRYABLE_AMOUNT_INR = 10  # ₹10

# How long after failure a retry is still valid (hours)
RETRY_WINDOW_HOURS = 72  # 3 days

# Estimated success rate for retries (used for projections — not guaranteed)
ESTIMATED_RETRY_SUCCESS_RATE = 0.70  # 70%


class PolicyDecision(NamedTuple):
    eligible: bool
    reason: str
    failure_category: str  # "transient" | "permanent" | "unknown"


def evaluate_transaction(transaction) -> PolicyDecision:
    """
    Deterministically evaluate whether a failed transaction is eligible for retry.

    This function is the single source of truth for retry eligibility.
    The AI cannot override this logic — it can only call tools that invoke it.
    """
    failure_code = (transaction.failure_code or "").lower().strip()
    amount = float(transaction.amount or 0)

    # Must be a failed transaction
    if transaction.status != "failed":
        return PolicyDecision(
            eligible=False,
            reason=f"Transaction status is '{transaction.status}', not 'failed'",
            failure_category="non_applicable",
        )

    # Failure code must be retryable
    if failure_code in NON_RETRYABLE_CODES:
        return PolicyDecision(
            eligible=False,
            reason=f"Failure code '{failure_code}' is non-retryable (permanent failure)",
            failure_category="permanent",
        )

    if failure_code not in RETRYABLE_FAILURE_CODES:
        return PolicyDecision(
            eligible=False,
            reason=f"Failure code '{failure_code}' is not in the approved retry list",
            failure_category="unknown",
        )

    # Amount bounds
    if amount < MIN_RETRYABLE_AMOUNT_INR:
        return PolicyDecision(
            eligible=False,
            reason=f"Amount ₹{amount:.2f} is below minimum threshold ₹{MIN_RETRYABLE_AMOUNT_INR}",
            failure_category="transient",
        )

    if amount > MAX_RETRYABLE_AMOUNT_INR:
        return PolicyDecision(
            eligible=False,
            reason=f"Amount ₹{amount:,.0f} exceeds maximum retryable threshold ₹{MAX_RETRYABLE_AMOUNT_INR:,}",
            failure_category="transient",
        )

    # Time window check
    if transaction.created_at:
        age_hours = (datetime.utcnow() - transaction.created_at).total_seconds() / 3600
        if age_hours > RETRY_WINDOW_HOURS:
            return PolicyDecision(
                eligible=False,
                reason=f"Transaction is {age_hours:.0f}h old, beyond {RETRY_WINDOW_HOURS}h retry window",
                failure_category="transient",
            )

    return PolicyDecision(
        eligible=True,
        reason=f"Eligible for Smart Retry: transient '{failure_code}' failure, within policy bounds",
        failure_category="transient",
    )


def get_policy_summary() -> dict:
    """Return human-readable policy configuration for display in the UI."""
    return {
        "retryable_failure_codes": sorted(RETRYABLE_FAILURE_CODES),
        "non_retryable_codes": sorted(NON_RETRYABLE_CODES),
        "max_retry_count": MAX_RETRY_COUNT,
        "max_amount_inr": MAX_RETRYABLE_AMOUNT_INR,
        "retry_window_hours": RETRY_WINDOW_HOURS,
        "estimated_success_rate_pct": int(ESTIMATED_RETRY_SUCCESS_RATE * 100),
    }
