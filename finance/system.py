# finance/system.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finance.models import BalanceSheet, CashFlow, CreditRating, IncomeStatement, Loan


@dataclass(slots=True)
class FinanceSystem:
    """Neutral financial statements and credit tools without industry-specific logic."""

    enabled: bool = False
    balance_sheet: BalanceSheet = field(default_factory=BalanceSheet)
    income_statement: IncomeStatement = field(default_factory=IncomeStatement)
    cash_flow: CashFlow = field(default_factory=CashFlow)
    loans: list[Loan] = field(default_factory=list)

    def process_tick(self, days: int) -> None:
        _ = days

    def quote_loan(
        self,
        principal: int,
        term_months: int,
        credit_rating: CreditRating,
        base_rate: float = 0.035,
    ) -> Loan:
        return Loan.quote(
            principal=principal,
            term_months=term_months,
            credit_rating=credit_rating,
            balance_sheet=self.balance_sheet,
            base_rate=base_rate,
        )

    def add_loan(self, loan: Loan) -> None:
        self.loans.append(loan)
        self.balance_sheet.add_asset("cash", loan.principal)
        self.balance_sheet.add_liability(f"loan:{loan.loan_id}", loan.principal)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "balance_sheet": self.balance_sheet.to_dict(),
            "income_statement": self.income_statement.to_dict(),
            "cash_flow": self.cash_flow.to_dict(),
            "loans": [loan.to_dict() for loan in self.loans],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> FinanceSystem:
        if data is None:
            return cls()

        return cls(
            enabled=bool(data.get("enabled", False)),
            balance_sheet=BalanceSheet.from_dict(data.get("balance_sheet", {})),
            income_statement=IncomeStatement.from_dict(data.get("income_statement", {})),
            cash_flow=CashFlow.from_dict(data.get("cash_flow", {})),
            loans=[Loan.from_dict(loan) for loan in data.get("loans", [])],
        )
