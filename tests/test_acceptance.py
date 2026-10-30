from datetime import date
from decimal import Decimal

import pytest

from cardcoach.engine import (
    CategoryRule,
    ComplaintCase,
    DraftError,
    PolicyValidationError,
    Rules,
    StatementSummary,
    Transaction,
    audit_rewards,
    category_bonus_spend,
    classify_fees,
    compare_cards,
    draft_complaint,
    mapping_findings,
    mask_pans,
    reconcile,
    validate_draft,
    validate_policy,
)


def txn(**kwargs) -> Transaction:
    defaults = dict(
        statement_id="stmt-feb",
        txn_date=date(2026, 1, 15),
        posting_date=date(2026, 1, 15),
        merchant_raw="STORE",
        merchant_normalised="store",
        amount=Decimal("1000"),
        type="purchase",
        channel=None,
        reward_points=None,
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def rules(**kwargs) -> Rules:
    defaults = dict(
        base_rate=Decimal("0"),
        rounding_unit=Decimal("1"),
        cap_period="calendar_month",
        bucket_by="posting_date",
        reward_lag="next_statement",
        fee_reversal_window_days=90,
        categories=(
            CategoryRule(
                name="store",
                merchants=("store",),
                rate=Decimal("0.05"),
                cap_amount=Decimal("100000"),
                source_url="https://bank.example/card",
                fetched_on="2026-10-30",
            ),
        ),
    )
    defaults.update(kwargs)
    return Rules(**defaults)


def summary(**kwargs) -> StatementSummary:
    defaults = dict(
        statement_id="stmt-feb",
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        currency="INR",
        country="IN",
        purchases=Decimal("0"),
        reward_earned=Decimal("0"),
    )
    defaults.update(kwargs)
    return StatementSummary(**defaults)


def test_01_statement_totals_reconcile():
    rows = [
        txn(amount=Decimal("100"), txn_date=date(2026, 2, 2), posting_date=date(2026, 2, 2)),
        txn(amount=Decimal("40"), txn_date=date(2026, 2, 3), posting_date=date(2026, 2, 3)),
        txn(type="fee", amount=Decimal("10"), merchant_raw="Annual fee"),
        txn(type="refund", amount=Decimal("5"), merchant_raw="STORE REFUND"),
        txn(type="payment", amount=Decimal("20"), merchant_raw="PAYMENT"),
    ]
    statement = summary(purchases=Decimal("140"), fees=Decimal("10"), refunds=Decimal("5"), payments=Decimal("20"))
    result = reconcile(rows, statement)
    assert result.ok
    assert result.totals["purchases"] == "140"
    assert result.mismatches == []

    broken = reconcile(rows, summary(purchases=Decimal("999"), fees=Decimal("10"), refunds=Decimal("5"), payments=Decimal("20")))
    assert not broken.ok
    assert any(item.startswith("purchases:") for item in broken.mismatches)


def test_02_previous_calendar_month_is_not_a_false_error():
    rows = [
        txn(amount=Decimal("1000"), txn_date=date(2026, 1, 15), posting_date=date(2026, 1, 15)),
        txn(amount=Decimal("2000"), txn_date=date(2026, 2, 10), posting_date=date(2026, 2, 10)),
    ]
    statement = summary(purchases=Decimal("3000"), reward_earned=Decimal("50"))
    findings = audit_rewards(rows, [statement], rules())
    assert not any(item.code in {"missing_points", "error", "mismatch"} for item in findings)


def test_03_last_day_purchase_posts_into_the_next_months_cap():
    card_rules = rules(
        categories=(
            CategoryRule(
                name="store",
                merchants=("store",),
                rate=Decimal("0.05"),
                cap_amount=Decimal("1000"),
                source_url="https://bank.example/card",
                fetched_on="2026-10-30",
            ),
        )
    )
    rows = [
        txn(amount=Decimal("1000"), txn_date=date(2026, 1, 15), posting_date=date(2026, 1, 15)),
        txn(amount=Decimal("400"), txn_date=date(2026, 1, 31), posting_date=date(2026, 2, 1)),
    ]
    usage = category_bonus_spend(rows, card_rules)
    assert usage["2026-01"] == Decimal("1000")
    assert usage["2026-02"] == Decimal("400")


def test_04_cap_is_not_reported_as_missing_points():
    card_rules = rules(
        categories=(
            CategoryRule(
                name="store",
                merchants=("store",),
                rate=Decimal("0.05"),
                cap_amount=Decimal("1000"),
                source_url="https://bank.example/card",
                fetched_on="2026-10-30",
            ),
        )
    )
    rows = [txn(amount=Decimal("1500"), txn_date=date(2026, 1, 20), posting_date=date(2026, 1, 20))]
    statement = summary(purchases=Decimal("1500"), reward_earned=Decimal("50"))
    findings = audit_rewards(rows, [statement], card_rules)
    assert any(item.code == "capped" for item in findings)
    assert not any(item.code == "missing_points" for item in findings)


def test_05_same_merchant_different_descriptors_are_flagged():
    rows = [
        txn(merchant_raw="Diverse Retails", merchant_normalised="cult.fit", amount=Decimal("1000"), reward_points=Decimal("10")),
        txn(merchant_raw="CULTFIT", merchant_normalised="cult.fit", amount=Decimal("1000"), reward_points=Decimal("50")),
    ]
    findings = mapping_findings(rows)
    assert any(item.code == "mapping" for item in findings)

    same_rate = [
        txn(merchant_raw="AMZN", merchant_normalised="amazon", reward_points=Decimal("50")),
        txn(merchant_raw="AMAZON", merchant_normalised="amazon", reward_points=Decimal("50")),
    ]
    assert mapping_findings(same_rate) == []


def test_06_fee_reversed_inside_the_window_is_not_an_error():
    rows = [
        txn(
            type="fee",
            amount=Decimal("1000"),
            txn_date=date(2026, 1, 1),
            posting_date=date(2026, 1, 1),
            merchant_raw="Annual membership fee",
            merchant_normalised="annual fee",
        ),
        txn(
            type="tax",
            amount=Decimal("180"),
            txn_date=date(2026, 1, 1),
            posting_date=date(2026, 1, 1),
            merchant_raw="GST",
            merchant_normalised="tax",
        ),
        txn(
            type="reversal",
            amount=Decimal("1180"),
            txn_date=date(2026, 3, 1),
            posting_date=date(2026, 3, 1),
            merchant_raw="Annual membership fee reversal",
            merchant_normalised="annual fee",
        ),
    ]
    findings = classify_fees(rows, window_days=90)
    assert [item.code for item in findings] == ["charged_then_reversed"]
    assert "error" not in {item.code for item in findings}


def test_07_card_comparison_states_net_value_and_assumptions():
    results = compare_cards(
        spend=[{"category": "fuel", "amount": Decimal("20000")}],
        cards=[
            {
                "name": "premium",
                "annual_fee": Decimal("1000"),
                "tax_rate": Decimal("0.18"),
                "base_rate": Decimal("0"),
                "rounding_unit": Decimal("1"),
                "opportunity_cost": Decimal("100"),
                "benefit_value": Decimal("200"),
                "assumptions": ["Fuel spend stays at 20000", "No cap on fuel"],
                "categories": [{"name": "fuel", "rate": Decimal("0.05"), "cap_amount": None}],
            }
        ],
    )
    result = results[0]
    assert result.rewards == Decimal("1000")
    assert result.fee_with_tax == Decimal("1180")
    assert result.net == Decimal("-80")
    assert "Fuel spend stays at 20000" in result.assumptions
    assert "annual_fee * (1 + tax_rate)" in result.formula
    assert result.formula in result.assumptions


def test_08_complaint_has_no_blanks_and_matches_the_maths():
    case = ComplaintCase(
        card_last4="4242",
        txn_dates=["15 Jan 2026"],
        amounts=[Decimal("5000")],
        statement_date="28 Feb 2026",
        billing_period="1 Feb 2026 to 28 Feb 2026",
        expected_points=Decimal("250"),
        received_points=Decimal("50"),
        ask="Please credit the 200 point shortfall and confirm in writing.",
        deadline="15 Nov 2026",
        currency="INR",
    )
    draft = draft_complaint(case)
    validate_draft(draft, case)
    assert "Shortfall: 200." in draft
    assert "Calculation: expected 250 minus received 50 = 200." in draft
    assert "4242" in draft

    with pytest.raises(DraftError):
        validate_draft(draft.replace("Shortfall: 200.", "Shortfall: 999."), case)
    with pytest.raises(DraftError):
        validate_draft(draft + "\nTODO fill the reference", case)
    with pytest.raises(DraftError):
        draft_complaint(
            ComplaintCase(
                card_last4="",
                txn_dates=["15 Jan 2026"],
                amounts=[Decimal("5000")],
                statement_date="28 Feb 2026",
                billing_period="1 Feb 2026 to 28 Feb 2026",
                expected_points=Decimal("250"),
                received_points=Decimal("50"),
                ask="Please credit the shortfall.",
                deadline="15 Nov 2026",
            )
        )


def test_09_policy_claim_without_source_and_fetch_date_fails():
    with pytest.raises(PolicyValidationError):
        validate_policy({"rate": "0.05"})
    with pytest.raises(PolicyValidationError):
        validate_policy({"source_url": "https://bank.example/card", "fetched_on": ""})
    validate_policy({"source_url": "https://bank.example/card", "fetched_on": "2026-10-30"})


def test_card_numbers_are_masked_to_the_last_four():
    masked = mask_pans("Paid with 4111111111111111 today.")
    assert "4111111111111111" not in masked
    assert masked.endswith("1111 today.") or "1111" in masked
    assert set(masked) & set("*")
