"""Deterministic credit-card maths.

Bank policy is not stored here. Callers pass rates, caps, and sources after
they have looked them up. Every money figure is a Decimal.

Reward points for one slice of spend:

    rounded = (amount // rounding_unit) * rounding_unit
    points = rounded * rate

Net annual value of a candidate card:

    net = rewards - annual_fee * (1 + tax_rate) - opportunity_cost + benefit_value
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path


class PolicyValidationError(ValueError):
    """A policy claim has no source URL or fetch date."""


class DraftError(ValueError):
    """A complaint draft is incomplete or the points maths do not match."""


_PAN = re.compile(r"\d(?:[ -]?\d){12,18}")
_PLACEHOLDER = re.compile(
    r"\{[^{}]+\}|\[(?:FILL|INSERT|TODO)[^\]]*\]|\bTODO\b|\bPLACEHOLDER\b|<[^>\n]+>",
    re.IGNORECASE,
)
_CURRENCY_COUNTRY = {
    "INR": "IN",
    "USD": "US",
    "GBP": "GB",
    "AED": "AE",
    "SGD": "SG",
    "AUD": "AU",
    "CAD": "CA",
}
_MONEY_FIELDS = ("purchases", "fees", "tax", "refunds", "payments", "interest", "emi")
_CREDIT_TYPES = frozenset({"refund", "credit", "reversal"})


def decimal_of(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def plain_number(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def mask_pans(text: str) -> str:
    """Replace a 13 to 19 digit card number with stars and the last four digits."""

    def replace(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if not 13 <= len(digits) <= 19:
            return match.group(0)
        return ("*" * (len(digits) - 4)) + digits[-4:]

    return _PAN.sub(replace, text)


def _norm(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _parse_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


@dataclass
class Transaction:
    statement_id: str
    txn_date: date
    posting_date: date | None
    merchant_raw: str
    merchant_normalised: str
    amount: Decimal
    type: str
    channel: str | None = None
    reward_points: Decimal | None = None


@dataclass
class StatementSummary:
    statement_id: str
    period_start: date
    period_end: date
    currency: str
    purchases: Decimal
    fees: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    refunds: Decimal = Decimal("0")
    payments: Decimal = Decimal("0")
    interest: Decimal = Decimal("0")
    emi: Decimal = Decimal("0")
    reward_opening: Decimal = Decimal("0")
    reward_earned: Decimal = Decimal("0")
    reward_adjusted: Decimal = Decimal("0")
    reward_closing: Decimal = Decimal("0")
    country: str | None = None
    total_due: Decimal | None = None
    opening_balance: Decimal | None = None


@dataclass
class CategoryRule:
    name: str
    merchants: tuple[str, ...]
    rate: Decimal
    cap_amount: Decimal | None = None
    exclusions: tuple[str, ...] = ()
    rounding_unit: Decimal | None = None
    source_url: str = ""
    fetched_on: str = ""


@dataclass
class Rules:
    base_rate: Decimal
    rounding_unit: Decimal
    cap_period: str = "calendar_month"
    bucket_by: str = "posting_date"
    reward_lag: str = "next_statement"
    fee_reversal_window_days: int = 90
    categories: tuple[CategoryRule, ...] = ()


@dataclass
class Finding:
    code: str
    message: str
    statement_id: str = ""
    period: str = ""
    expected: Decimal | None = None
    actual: Decimal | None = None
    confidence: str = "high"
    fact: str = ""
    sourced_policy: str = ""
    inference: str = ""


@dataclass
class Reconciliation:
    statement_id: str
    ok: bool
    mismatches: list[str] = field(default_factory=list)
    totals: dict[str, str] = field(default_factory=dict)


@dataclass
class ComplaintCase:
    card_last4: str
    txn_dates: list[str]
    amounts: list[Decimal]
    statement_date: str
    billing_period: str
    expected_points: Decimal
    received_points: Decimal
    ask: str
    deadline: str
    reference: str | None = None
    currency: str = ""


@dataclass
class CardResult:
    name: str
    rewards: Decimal
    fee_with_tax: Decimal
    opportunity_cost: Decimal
    benefit_value: Decimal
    net: Decimal
    assumptions: list[str]
    formula: str


def validate_policy(claim: dict) -> None:
    url = str(claim.get("source_url") or "").strip()
    fetched = str(claim.get("fetched_on") or "").strip()
    if not url or not fetched:
        raise PolicyValidationError(
            "A policy claim needs source_url and fetched_on. The auditor does not supply them."
        )


def detect_locale(summary: StatementSummary) -> dict[str, str | None]:
    currency = (summary.currency or "").upper() or None
    country = summary.country or (_CURRENCY_COUNTRY.get(currency) if currency else None)
    return {"currency": currency, "country": country}


def points_for(amount: Decimal, rate: Decimal, rounding_unit: Decimal) -> Decimal:
    """Points for one slice of spend after per-transaction rounding."""
    if amount <= 0 or rate == 0:
        return Decimal("0")
    rounded = amount
    if rounding_unit > 0:
        rounded = (amount // rounding_unit) * rounding_unit
    return rounded * rate


def _bucket_date(txn: Transaction, rules: Rules) -> date:
    if rules.bucket_by == "posting_date" and txn.posting_date is not None:
        return txn.posting_date
    return txn.posting_date or txn.txn_date


def bucket_month(txn: Transaction, rules: Rules) -> str:
    """Calendar month, or statement id, that this transaction counts against."""
    if rules.cap_period == "statement_cycle":
        return txn.statement_id
    counted = _bucket_date(txn, rules)
    return f"{counted.year:04d}-{counted.month:02d}"


def reward_month_for(summary: StatementSummary, rules: Rules) -> str:
    """Month whose points this statement's reward line is expected to show."""
    if rules.reward_lag == "next_statement":
        previous = summary.period_end.replace(day=1) - timedelta(days=1)
        return f"{previous.year:04d}-{previous.month:02d}"
    return f"{summary.period_end.year:04d}-{summary.period_end.month:02d}"


def _category_for(txn: Transaction, rules: Rules) -> CategoryRule | None:
    name = _norm(txn.merchant_normalised)
    for category in rules.categories:
        if name in {_norm(merchant) for merchant in category.merchants}:
            return category
    return None


def _is_excluded(txn: Transaction, category: CategoryRule) -> bool:
    banned = {_norm(item) for item in category.exclusions}
    return _norm(txn.type) in banned or _norm(txn.channel) in banned


def _month_slices(
    transactions: list[Transaction], rules: Rules
) -> dict[str, dict[str, list[Transaction]]]:
    grouped: dict[str, dict[str, list[Transaction]]] = defaultdict(lambda: defaultdict(list))
    for txn in transactions:
        if txn.type not in {"purchase", "refund"}:
            continue
        category = _category_for(txn, rules)
        key = category.name if category is not None else ""
        grouped[bucket_month(txn, rules)][key].append(txn)
    return grouped


def _score_group(
    txns: list[Transaction],
    rate: Decimal,
    base_rate: Decimal,
    cap_amount: Decimal | None,
    rounding_unit: Decimal,
    exclusions: tuple[str, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    """Return points, bonus spend, and spend above the cap."""
    category = CategoryRule(
        name="",
        merchants=(),
        rate=rate,
        cap_amount=cap_amount,
        exclusions=exclusions,
        rounding_unit=rounding_unit,
    )
    remaining = cap_amount
    points = Decimal("0")
    bonus_spend = Decimal("0")
    above_cap = Decimal("0")
    ordered = sorted(txns, key=lambda txn: (_bucket_date(txn, Rules(base_rate, rounding_unit)), txn.txn_date))
    for txn in ordered:
        if _is_excluded(txn, category):
            if txn.type == "purchase":
                points += points_for(txn.amount, base_rate, rounding_unit)
            elif txn.type == "refund":
                points -= points_for(txn.amount, base_rate, rounding_unit)
            continue
        if txn.type == "refund":
            from_bonus = min(txn.amount, bonus_spend)
            from_base = txn.amount - from_bonus
            points -= points_for(from_bonus, rate, rounding_unit)
            points -= points_for(from_base, base_rate, rounding_unit)
            bonus_spend -= from_bonus
            above_cap = max(above_cap - from_base, Decimal("0"))
            if remaining is not None:
                remaining += from_bonus
            continue
        if txn.type != "purchase":
            continue
        if remaining is None:
            bonus_part = txn.amount
        else:
            bonus_part = min(txn.amount, max(remaining, Decimal("0")))
            remaining -= bonus_part
        base_part = txn.amount - bonus_part
        bonus_spend += bonus_part
        above_cap += base_part
        points += points_for(bonus_part, rate, rounding_unit)
        points += points_for(base_part, base_rate, rounding_unit)
    return points, bonus_spend, above_cap


def category_bonus_spend(transactions: list[Transaction], rules: Rules) -> dict[str, Decimal]:
    """Spend that consumed each month's bonus cap, keyed by YYYY-MM or statement id."""
    usage: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for month, groups in _month_slices(transactions, rules).items():
        for name, txns in groups.items():
            category = next((item for item in rules.categories if item.name == name), None)
            if category is None:
                continue
            unit = category.rounding_unit or rules.rounding_unit
            _, bonus_spend, _ = _score_group(
                txns,
                category.rate,
                rules.base_rate,
                category.cap_amount,
                unit,
                category.exclusions,
            )
            usage[month] += bonus_spend
    return dict(usage)


def expected_points_for_month(
    transactions: list[Transaction], rules: Rules, month: str
) -> tuple[Decimal, Decimal]:
    """Return expected points and spend above bonus caps for one bucket."""
    groups = _month_slices(transactions, rules).get(month, {})
    points = Decimal("0")
    above_cap = Decimal("0")
    for name, txns in groups.items():
        category = next((item for item in rules.categories if item.name == name), None)
        if category is None:
            for txn in txns:
                sign = Decimal("-1") if txn.type == "refund" else Decimal("1")
                points += sign * points_for(txn.amount, rules.base_rate, rules.rounding_unit)
            continue
        unit = category.rounding_unit or rules.rounding_unit
        group_points, _, group_above = _score_group(
            txns,
            category.rate,
            rules.base_rate,
            category.cap_amount,
            unit,
            category.exclusions,
        )
        points += group_points
        above_cap += group_above
    return points, above_cap


def audit_rewards(
    transactions: list[Transaction],
    summaries: list[StatementSummary],
    rules: Rules,
) -> list[Finding]:
    """Compare each statement's reward line with the month the bank is paying for.

    A next-statement lag means the line belongs to the previous calendar month.
    Spend past a cap produces a capped finding. It is a missing-points finding
    only when the credited points are below the capped expectation.
    """
    findings: list[Finding] = []
    for summary in summaries:
        month = reward_month_for(summary, rules)
        expected, above_cap = expected_points_for_month(transactions, rules, month)
        actual = summary.reward_earned
        policy = (
            f"bucket_by={rules.bucket_by}; cap_period={rules.cap_period}; "
            f"reward_lag={rules.reward_lag}"
        )
        if above_cap > 0:
            findings.append(
                Finding(
                    code="capped",
                    message=(
                        f"{month} had {plain_number(above_cap)} of spend above the bonus cap. "
                        f"Expected points after the cap are {plain_number(expected)}. "
                        "This is capped, not missing points."
                    ),
                    statement_id=summary.statement_id,
                    period=month,
                    expected=expected,
                    actual=actual,
                    fact=f"Reward line on {summary.statement_id} is {plain_number(actual)}.",
                    sourced_policy=policy,
                    inference="The shortfall against the headline rate is the cap, when the credited points match this expectation.",
                )
            )
        if actual < expected:
            findings.append(
                Finding(
                    code="missing_points",
                    message=(
                        f"Expected {plain_number(expected)} points for {month} after caps, "
                        f"exclusions, refunds, and rounding. The statement shows {plain_number(actual)}."
                    ),
                    statement_id=summary.statement_id,
                    period=month,
                    expected=expected,
                    actual=actual,
                    fact=f"Reward earned on the statement is {plain_number(actual)}.",
                    sourced_policy=policy,
                    inference="Credited points are below the capped expectation.",
                )
            )
    return findings


def reconcile(transactions: list[Transaction], summary: StatementSummary) -> Reconciliation:
    """Sum one statement's rows and compare them with its summary."""
    mine = [txn for txn in transactions if txn.statement_id == summary.statement_id]
    totals = {name: Decimal("0") for name in _MONEY_FIELDS}
    type_to_field = {
        "purchase": "purchases",
        "refund": "refunds",
        "payment": "payments",
        "fee": "fees",
        "tax": "tax",
        "interest": "interest",
        "emi": "emi",
    }
    for txn in mine:
        field_name = type_to_field.get(txn.type)
        if field_name:
            totals[field_name] += txn.amount
    mismatches: list[str] = []
    for name in _MONEY_FIELDS:
        stated = getattr(summary, name)
        if totals[name] != stated:
            mismatches.append(
                f"{name}: rows sum to {plain_number(totals[name])}, summary says {plain_number(stated)}"
            )
    if summary.total_due is not None and summary.opening_balance is not None:
        expected_due = (
            summary.opening_balance
            - totals["payments"]
            - totals["refunds"]
            + totals["purchases"]
            + totals["fees"]
            + totals["tax"]
            + totals["interest"]
            + totals["emi"]
        )
        if expected_due != summary.total_due:
            mismatches.append(
                f"total_due: rows imply {plain_number(expected_due)}, summary says {plain_number(summary.total_due)}"
            )
    return Reconciliation(
        statement_id=summary.statement_id,
        ok=not mismatches,
        mismatches=mismatches,
        totals={name: plain_number(value) for name, value in totals.items()},
    )


def classify_fees(transactions: list[Transaction], window_days: int) -> list[Finding]:
    """A fee followed by a matching credit inside the window was charged, then reversed."""
    findings: list[Finding] = []
    fees = [txn for txn in transactions if txn.type == "fee"]
    credits = [txn for txn in transactions if txn.type in _CREDIT_TYPES]
    for fee in fees:
        fee_date = fee.posting_date or fee.txn_date
        tax = sum(
            (
                txn.amount
                for txn in transactions
                if txn.type == "tax"
                and txn.statement_id == fee.statement_id
                and txn.txn_date == fee.txn_date
            ),
            Decimal("0"),
        )
        targets = {fee.amount, fee.amount + tax}
        match = None
        for credit in credits:
            credit_date = credit.posting_date or credit.txn_date
            if credit_date < fee_date:
                continue
            if (credit_date - fee_date).days > window_days:
                continue
            if credit.amount in targets:
                match = credit
                break
        if match is None:
            continue
        findings.append(
            Finding(
                code="charged_then_reversed",
                message=(
                    f"Fee of {plain_number(fee.amount)} on {fee_date.isoformat()} "
                    f"was reversed by {plain_number(match.amount)} on "
                    f"{(match.posting_date or match.txn_date).isoformat()} "
                    f"within {window_days} days."
                ),
                statement_id=fee.statement_id,
                period=fee_date.isoformat(),
                expected=fee.amount + tax,
                actual=match.amount,
                fact="The statement has both the fee and a later credit.",
                sourced_policy=f"Reversal window is {window_days} days.",
                inference="This is charged then reversed, not an error.",
            )
        )
    return findings


def mapping_findings(transactions: list[Transaction]) -> list[Finding]:
    """Flag one normalised merchant whose raw descriptors were rewarded differently."""
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        if txn.merchant_normalised and txn.type == "purchase":
            grouped[_norm(txn.merchant_normalised)].append(txn)
    findings: list[Finding] = []
    for name, txns in grouped.items():
        ratios: dict[str, Decimal] = {}
        for txn in txns:
            if txn.reward_points is None or txn.amount == 0:
                continue
            ratios[txn.merchant_raw] = (txn.reward_points / txn.amount).quantize(Decimal("0.0001"))
        distinct = {ratio for ratio in ratios.values()}
        if len(ratios) >= 2 and len(distinct) > 1:
            shown = ", ".join(f"{raw} -> {plain_number(ratio)}" for raw, ratio in sorted(ratios.items()))
            findings.append(
                Finding(
                    code="mapping",
                    message=f"Possible descriptor mismatch for {name}: {shown}.",
                    fact="The same normalised merchant has more than one raw descriptor.",
                    inference="The reward treatment differs, so the names may be the wrong merchant or a different category.",
                    confidence="medium",
                )
            )
    return findings


def _card_rewards(spend: list[dict], card: dict) -> Decimal:
    categories = []
    for raw in card.get("categories", []):
        categories.append(
            CategoryRule(
                name=str(raw["name"]),
                merchants=(str(raw["name"]),),
                rate=decimal_of(raw["rate"]),
                cap_amount=None if raw.get("cap_amount") in (None, "") else decimal_of(raw["cap_amount"]),
                rounding_unit=None
                if raw.get("rounding_unit") in (None, "")
                else decimal_of(raw["rounding_unit"]),
            )
        )
    rules = Rules(
        base_rate=decimal_of(card.get("base_rate", "0")),
        rounding_unit=decimal_of(card.get("rounding_unit", "1")),
        categories=tuple(categories),
    )
    by_category: dict[str, list[Transaction]] = defaultdict(list)
    for index, item in enumerate(spend):
        by_category[str(item["category"])].append(
            Transaction(
                statement_id="comparison",
                txn_date=date(2000, 1, 1),
                posting_date=date(2000, 1, 1 + index if index < 27 else 1),
                merchant_raw=str(item["category"]),
                merchant_normalised=str(item["category"]),
                amount=decimal_of(item["amount"]),
                type="purchase",
            )
        )
    rewards = Decimal("0")
    for name, txns in by_category.items():
        category = next((item for item in categories if item.name == name), None)
        if category is None:
            for txn in txns:
                rewards += points_for(txn.amount, rules.base_rate, rules.rounding_unit)
            continue
        unit = category.rounding_unit or rules.rounding_unit
        group_points, _, _ = _score_group(
            txns,
            category.rate,
            rules.base_rate,
            category.cap_amount,
            unit,
            (),
        )
        rewards += group_points
    return rewards


def compare_cards(spend: list[dict], cards: list[dict]) -> list[CardResult]:
    """Net annual value after fee, tax, opportunity cost, and stated benefits."""
    formula = "net = rewards - annual_fee * (1 + tax_rate) - opportunity_cost + benefit_value"
    results: list[CardResult] = []
    for card in cards:
        rewards = _card_rewards(spend, card)
        fee_with_tax = decimal_of(card.get("annual_fee", "0")) * (
            Decimal("1") + decimal_of(card.get("tax_rate", "0"))
        )
        opportunity = decimal_of(card.get("opportunity_cost", "0"))
        benefit = decimal_of(card.get("benefit_value", "0"))
        net = rewards - fee_with_tax - opportunity + benefit
        assumptions = [formula, *list(card.get("assumptions") or [])]
        results.append(
            CardResult(
                name=str(card["name"]),
                rewards=rewards,
                fee_with_tax=fee_with_tax,
                opportunity_cost=opportunity,
                benefit_value=benefit,
                net=net,
                assumptions=assumptions,
                formula=formula,
            )
        )
    return results


def draft_complaint(case: ComplaintCase) -> str:
    """Build a factual complaint. Refuses to leave a required fact blank."""
    last4 = re.sub(r"\D", "", case.card_last4)[-4:]
    required = {
        "card_last4": last4,
        "statement_date": case.statement_date.strip(),
        "billing_period": case.billing_period.strip(),
        "ask": case.ask.strip(),
        "deadline": case.deadline.strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if not case.txn_dates or not case.amounts or len(case.txn_dates) != len(case.amounts):
        missing.append("transactions")
    if missing:
        raise DraftError("Missing facts: " + ", ".join(missing))
    expected = decimal_of(case.expected_points)
    received = decimal_of(case.received_points)
    shortfall = expected - received
    lines = [
        "Hello,",
        "",
        f"Card ending {last4}.",
        f"Statement date: {case.statement_date.strip()}.",
        f"Billing period: {case.billing_period.strip()}.",
        "Transactions:",
    ]
    for when, amount in zip(case.txn_dates, case.amounts):
        amount_text = plain_number(decimal_of(amount))
        suffix = f" {case.currency}" if case.currency else ""
        lines.append(f"- {when}: {amount_text}{suffix}")
    lines.extend(
        [
            f"Points expected: {plain_number(expected)}.",
            f"Points received: {plain_number(received)}.",
            f"Shortfall: {plain_number(shortfall)}.",
            (
                f"Calculation: expected {plain_number(expected)} minus received "
                f"{plain_number(received)} = {plain_number(shortfall)}."
            ),
            case.ask.strip(),
            f"Please reply by {case.deadline.strip()}.",
        ]
    )
    if case.reference and case.reference.strip():
        lines.append(f"Reference: {case.reference.strip()}.")
    return mask_pans("\n".join(lines))


def validate_draft(draft: str, case: ComplaintCase) -> None:
    if _PLACEHOLDER.search(draft):
        raise DraftError("The draft still has a placeholder.")
    expected = plain_number(decimal_of(case.expected_points))
    received = plain_number(decimal_of(case.received_points))
    shortfall = plain_number(decimal_of(case.expected_points) - decimal_of(case.received_points))
    last4 = re.sub(r"\D", "", case.card_last4)[-4:]
    for token, label in (
        (expected, "expected points"),
        (received, "received points"),
        (shortfall, "shortfall"),
        (last4, "card last four"),
    ):
        if token not in draft:
            raise DraftError(f"The draft is missing {label} ({token}).")
    if f"Shortfall: {shortfall}." not in draft:
        raise DraftError("Expected-versus-received maths do not match the case.")
    digits = re.sub(r"\D", "", case.card_last4)
    if len(digits) > 4 and digits in draft:
        raise DraftError("The draft contains a full card number.")


def _finding_dict(finding: Finding) -> dict:
    return {
        "code": finding.code,
        "message": finding.message,
        "statement_id": finding.statement_id,
        "period": finding.period,
        "expected": None if finding.expected is None else plain_number(finding.expected),
        "actual": None if finding.actual is None else plain_number(finding.actual),
        "confidence": finding.confidence,
        "fact": finding.fact,
        "sourced_policy": finding.sourced_policy,
        "inference": finding.inference,
    }


def run_audit(
    transactions: list[Transaction],
    summaries: list[StatementSummary],
    rules: Rules,
) -> dict:
    reconciliations = [reconcile(transactions, summary) for summary in summaries]
    findings: list[Finding] = []
    for item in reconciliations:
        if not item.ok:
            findings.append(
                Finding(
                    code="mismatch",
                    message="; ".join(item.mismatches),
                    statement_id=item.statement_id,
                    confidence="high",
                    fact="Transaction rows and the statement summary disagree.",
                    inference="Stop the reward audit for this statement until the rows match.",
                )
            )
    if all(item.ok for item in reconciliations):
        findings.extend(audit_rewards(transactions, summaries, rules))
        findings.extend(classify_fees(transactions, rules.fee_reversal_window_days))
        findings.extend(mapping_findings(transactions))
    return {
        "ok": all(item.ok for item in reconciliations),
        "locales": [detect_locale(summary) for summary in summaries],
        "reconciliation": [
            {
                "statement_id": item.statement_id,
                "ok": item.ok,
                "mismatches": item.mismatches,
                "totals": item.totals,
            }
            for item in reconciliations
        ],
        "findings": [_finding_dict(finding) for finding in findings],
    }


def transaction_from_dict(raw: dict) -> Transaction:
    points = raw.get("reward_points")
    return Transaction(
        statement_id=str(raw["statement_id"]),
        txn_date=_parse_date(raw["txn_date"]) or date.min,
        posting_date=_parse_date(raw.get("posting_date")),
        merchant_raw=str(raw.get("merchant_raw") or ""),
        merchant_normalised=str(raw.get("merchant_normalised") or ""),
        amount=decimal_of(raw["amount"]),
        type=str(raw["type"]),
        channel=str(raw["channel"]) if raw.get("channel") else None,
        reward_points=None if points in (None, "") else decimal_of(points),
    )


def summary_from_dict(raw: dict) -> StatementSummary:
    total_due = raw.get("total_due")
    opening = raw.get("opening_balance")
    return StatementSummary(
        statement_id=str(raw["statement_id"]),
        period_start=_parse_date(raw["period_start"]) or date.min,
        period_end=_parse_date(raw["period_end"]) or date.min,
        currency=str(raw.get("currency") or ""),
        purchases=decimal_of(raw.get("purchases", "0")),
        fees=decimal_of(raw.get("fees", "0")),
        tax=decimal_of(raw.get("tax", "0")),
        refunds=decimal_of(raw.get("refunds", "0")),
        payments=decimal_of(raw.get("payments", "0")),
        interest=decimal_of(raw.get("interest", "0")),
        emi=decimal_of(raw.get("emi", "0")),
        reward_opening=decimal_of(raw.get("reward_opening", "0")),
        reward_earned=decimal_of(raw.get("reward_earned", "0")),
        reward_adjusted=decimal_of(raw.get("reward_adjusted", "0")),
        reward_closing=decimal_of(raw.get("reward_closing", "0")),
        country=str(raw["country"]) if raw.get("country") else None,
        total_due=None if total_due in (None, "") else decimal_of(total_due),
        opening_balance=None if opening in (None, "") else decimal_of(opening),
    )


def rules_from_dict(raw: dict) -> Rules:
    categories = []
    for item in raw.get("categories", []):
        cap = item.get("cap_amount")
        unit = item.get("rounding_unit")
        categories.append(
            CategoryRule(
                name=str(item["name"]),
                merchants=tuple(str(merchant) for merchant in item.get("merchants", [])),
                rate=decimal_of(item["rate"]),
                cap_amount=None if cap in (None, "") else decimal_of(cap),
                exclusions=tuple(str(value) for value in item.get("exclusions", [])),
                rounding_unit=None if unit in (None, "") else decimal_of(unit),
                source_url=str(item.get("source_url") or ""),
                fetched_on=str(item.get("fetched_on") or ""),
            )
        )
    return Rules(
        base_rate=decimal_of(raw.get("base_rate", "0")),
        rounding_unit=decimal_of(raw.get("rounding_unit", "1")),
        cap_period=str(raw.get("cap_period") or "calendar_month"),
        bucket_by=str(raw.get("bucket_by") or "posting_date"),
        reward_lag=str(raw.get("reward_lag") or "next_statement"),
        fee_reversal_window_days=int(raw.get("fee_reversal_window_days") or 90),
        categories=tuple(categories),
    )


def load_transactions(path: Path) -> list[Transaction]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["transactions"] if isinstance(payload, dict) else payload
        return [transaction_from_dict(row) for row in rows]
    with path.open(newline="", encoding="utf-8") as handle:
        return [transaction_from_dict(row) for row in csv.DictReader(handle)]


def load_summaries(path: Path) -> list[StatementSummary]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["statements"] if isinstance(payload, dict) and "statements" in payload else payload
    if isinstance(rows, dict):
        rows = [rows]
    return [summary_from_dict(row) for row in rows]


def load_rules(path: Path) -> Rules:
    return rules_from_dict(json.loads(path.read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cardcoach", description="Reconcile and audit card statements.")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="Reconcile rows and audit rewards, fees, and descriptors.")
    audit.add_argument("--transactions", required=True, type=Path)
    audit.add_argument("--rules", required=True, type=Path)
    audit.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "audit":
        report = run_audit(
            load_transactions(args.transactions),
            load_summaries(args.summary),
            load_rules(args.rules),
        )
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
