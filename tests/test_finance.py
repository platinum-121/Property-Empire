# tests/test_finance.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from finance.models import BalanceSheet, CashFlow, CreditBand, CreditRating, IncomeStatement, Loan
from finance.system import FinanceSystem


def test_balance_sheet_tracks_assets_liabilities_equity_and_leverage() -> None:
    balance_sheet = BalanceSheet(
        assets={"cash": 500000, "property": 1500000},
        liabilities={"loans": 800000},
        equity={"owner_equity": 1200000},
    )

    assert balance_sheet.total_assets == 2000000
    assert balance_sheet.total_liabilities == 800000
    assert balance_sheet.total_equity == 1200000
    assert balance_sheet.is_balanced
    assert balance_sheet.leverage_ratio == 0.4


def test_income_statement_tracks_revenue_expenses_and_profit() -> None:
    statement = IncomeStatement()

    statement.add_revenue("rent", 250000)
    statement.add_revenue("fees", 50000)
    statement.add_expense("payroll", 100000)
    statement.add_expense("maintenance", 25000)

    assert statement.total_revenue == 300000
    assert statement.total_expenses == 125000
    assert statement.profit == 175000


def test_cash_flow_tracks_net_cash_flow() -> None:
    cash_flow = CashFlow()

    cash_flow.add_operating("operations", 125000)
    cash_flow.add_investing("asset_purchase", -50000)
    cash_flow.add_financing("loan_draw", 200000)

    assert cash_flow.operating_cash_flow == 125000
    assert cash_flow.investing_cash_flow == -50000
    assert cash_flow.financing_cash_flow == 200000
    assert cash_flow.net_cash_flow == 275000


def test_credit_rating_uses_zero_to_800_scale() -> None:
    prime = CreditRating(score=790)

    assert prime.band is CreditBand.PRIME
    assert prime.risk_factor == 0.0125

    try:
        CreditRating(score=801)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected credit scores above 800 to be rejected.")


def test_loans_are_affected_by_credit_score() -> None:
    balance_sheet = BalanceSheet(assets={"cash": 1000000}, liabilities={"debt": 200000})

    strong_loan = Loan.quote(
        principal=100000,
        term_months=60,
        credit_rating=CreditRating(score=760),
        balance_sheet=balance_sheet,
    )
    weak_loan = Loan.quote(
        principal=100000,
        term_months=60,
        credit_rating=CreditRating(score=320),
        balance_sheet=balance_sheet,
    )

    assert weak_loan.annual_interest_rate > strong_loan.annual_interest_rate


def test_loans_are_affected_by_leverage() -> None:
    rating = CreditRating(score=700)
    low_leverage = BalanceSheet(assets={"cash": 1000000}, liabilities={"debt": 100000})
    high_leverage = BalanceSheet(assets={"cash": 1000000}, liabilities={"debt": 900000})

    low_rate_loan = Loan.quote(
        principal=100000,
        term_months=36,
        credit_rating=rating,
        balance_sheet=low_leverage,
    )
    high_rate_loan = Loan.quote(
        principal=100000,
        term_months=36,
        credit_rating=rating,
        balance_sheet=high_leverage,
    )

    assert high_rate_loan.annual_interest_rate > low_rate_loan.annual_interest_rate


def test_finance_system_adds_loan_to_balance_sheet() -> None:
    finance = FinanceSystem()
    loan = finance.quote_loan(
        principal=250000,
        term_months=48,
        credit_rating=CreditRating(score=650),
    )

    finance.add_loan(loan)

    assert finance.loans == [loan]
    assert finance.balance_sheet.assets["cash"] == 250000
    assert finance.balance_sheet.liabilities[f"loan:{loan.loan_id}"] == 250000
