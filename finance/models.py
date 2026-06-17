# finance/models.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


Money = int


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _validate_non_negative(name: str, value: int | float) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _sum_values(values: dict[str, Money]) -> Money:
    return sum(values.values())


@dataclass(slots=True)
class BalanceSheet:
    assets: dict[str, Money] = field(default_factory=dict)
    liabilities: dict[str, Money] = field(default_factory=dict)
    equity: dict[str, Money] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for bucket_name, bucket in (
            ("assets", self.assets),
            ("liabilities", self.liabilities),
            ("equity", self.equity),
        ):
            for line_name, value in bucket.items():
                _validate_non_negative(f"{bucket_name}.{line_name}", value)

    @property
    def total_assets(self) -> Money:
        return _sum_values(self.assets)

    @property
    def total_liabilities(self) -> Money:
        return _sum_values(self.liabilities)

    @property
    def total_equity(self) -> Money:
        explicit_equity = _sum_values(self.equity)
        if explicit_equity:
            return explicit_equity

        return self.total_assets - self.total_liabilities

    @property
    def leverage_ratio(self) -> float:
        if self.total_assets <= 0:
            return 0.0

        return self.total_liabilities / self.total_assets

    @property
    def is_balanced(self) -> bool:
        return self.total_assets == self.total_liabilities + self.total_equity

    def add_asset(self, name: str, value: Money) -> None:
        _validate_non_negative(name, value)
        self.assets[name] = self.assets.get(name, 0) + value

    def add_liability(self, name: str, value: Money) -> None:
        _validate_non_negative(name, value)
        self.liabilities[name] = self.liabilities.get(name, 0) + value

    def add_equity(self, name: str, value: Money) -> None:
        _validate_non_negative(name, value)
        self.equity[name] = self.equity.get(name, 0) + value

    def to_dict(self) -> dict[str, Any]:
        return {
            "assets": self.assets,
            "liabilities": self.liabilities,
            "equity": self.equity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BalanceSheet:
        return cls(
            assets={str(key): int(value) for key, value in data.get("assets", {}).items()},
            liabilities={
                str(key): int(value) for key, value in data.get("liabilities", {}).items()
            },
            equity={str(key): int(value) for key, value in data.get("equity", {}).items()},
        )


@dataclass(slots=True)
class IncomeStatement:
    revenue: dict[str, Money] = field(default_factory=dict)
    expenses: dict[str, Money] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for bucket_name, bucket in (("revenue", self.revenue), ("expenses", self.expenses)):
            for line_name, value in bucket.items():
                _validate_non_negative(f"{bucket_name}.{line_name}", value)

    @property
    def total_revenue(self) -> Money:
        return _sum_values(self.revenue)

    @property
    def total_expenses(self) -> Money:
        return _sum_values(self.expenses)

    @property
    def profit(self) -> Money:
        return self.total_revenue - self.total_expenses

    def add_revenue(self, name: str, value: Money) -> None:
        _validate_non_negative(name, value)
        self.revenue[name] = self.revenue.get(name, 0) + value

    def add_expense(self, name: str, value: Money) -> None:
        _validate_non_negative(name, value)
        self.expenses[name] = self.expenses.get(name, 0) + value

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue": self.revenue,
            "expenses": self.expenses,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IncomeStatement:
        return cls(
            revenue={str(key): int(value) for key, value in data.get("revenue", {}).items()},
            expenses={str(key): int(value) for key, value in data.get("expenses", {}).items()},
        )


@dataclass(slots=True)
class CashFlow:
    operating: dict[str, Money] = field(default_factory=dict)
    investing: dict[str, Money] = field(default_factory=dict)
    financing: dict[str, Money] = field(default_factory=dict)

    @property
    def operating_cash_flow(self) -> Money:
        return _sum_values(self.operating)

    @property
    def investing_cash_flow(self) -> Money:
        return _sum_values(self.investing)

    @property
    def financing_cash_flow(self) -> Money:
        return _sum_values(self.financing)

    @property
    def net_cash_flow(self) -> Money:
        return self.operating_cash_flow + self.investing_cash_flow + self.financing_cash_flow

    def add_operating(self, name: str, value: Money) -> None:
        self.operating[name] = self.operating.get(name, 0) + value

    def add_investing(self, name: str, value: Money) -> None:
        self.investing[name] = self.investing.get(name, 0) + value

    def add_financing(self, name: str, value: Money) -> None:
        self.financing[name] = self.financing.get(name, 0) + value

    def to_dict(self) -> dict[str, Any]:
        return {
            "operating": self.operating,
            "investing": self.investing,
            "financing": self.financing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CashFlow:
        return cls(
            operating={str(key): int(value) for key, value in data.get("operating", {}).items()},
            investing={str(key): int(value) for key, value in data.get("investing", {}).items()},
            financing={str(key): int(value) for key, value in data.get("financing", {}).items()},
        )


class CreditBand(Enum):
    DISTRESSED = "Distressed"
    HIGH_RISK = "High Risk"
    SPECULATIVE = "Speculative"
    STABLE = "Stable"
    STRONG = "Strong"
    PRIME = "Prime"


@dataclass(frozen=True, slots=True)
class CreditRating:
    score: int

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 800:
            raise ValueError("Credit score must be between 0 and 800.")

    @property
    def band(self) -> CreditBand:
        if self.score < 200:
            return CreditBand.DISTRESSED
        if self.score < 350:
            return CreditBand.HIGH_RISK
        if self.score < 500:
            return CreditBand.SPECULATIVE
        if self.score < 650:
            return CreditBand.STABLE
        if self.score < 750:
            return CreditBand.STRONG
        return CreditBand.PRIME

    @property
    def risk_factor(self) -> float:
        return (800 - self.score) / 800

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreditRating:
        return cls(score=int(data["score"]))


@dataclass(slots=True)
class Loan:
    principal: Money
    annual_interest_rate: float
    term_months: int
    credit_rating: CreditRating
    leverage_ratio: float
    loan_id: str = field(default_factory=lambda: _new_id("loan"))
    remaining_term_months: int | None = None
    original_principal: Money | None = None
    name: str = "Property Loan"
    secured_asset_id: str | None = None
    status: str = "Current"

    def __post_init__(self) -> None:
        _validate_non_negative("principal", self.principal)
        _validate_non_negative("annual_interest_rate", self.annual_interest_rate)
        _validate_non_negative("leverage_ratio", self.leverage_ratio)
        if self.term_months < 1:
            raise ValueError("Loan term must be at least one month.")
        if self.remaining_term_months is None:
            self.remaining_term_months = self.term_months
        if self.original_principal is None:
            self.original_principal = self.principal
        if not 0 <= self.remaining_term_months <= self.term_months:
            raise ValueError("remaining_term_months must be between zero and term_months.")
        _validate_non_negative("original_principal", self.original_principal)

    @classmethod
    def quote(
        cls,
        principal: Money,
        term_months: int,
        credit_rating: CreditRating,
        balance_sheet: BalanceSheet,
        base_rate: float = 0.035,
    ) -> Loan:
        leverage_ratio = balance_sheet.leverage_ratio
        annual_interest_rate = cls.calculate_interest_rate(
            credit_rating=credit_rating,
            leverage_ratio=leverage_ratio,
            base_rate=base_rate,
        )
        return cls(
            principal=principal,
            annual_interest_rate=annual_interest_rate,
            term_months=term_months,
            credit_rating=credit_rating,
            leverage_ratio=leverage_ratio,
        )

    @staticmethod
    def calculate_interest_rate(
        credit_rating: CreditRating,
        leverage_ratio: float,
        base_rate: float = 0.035,
    ) -> float:
        _validate_non_negative("base_rate", base_rate)
        _validate_non_negative("leverage_ratio", leverage_ratio)
        credit_penalty = credit_rating.risk_factor * 0.12
        leverage_penalty = min(leverage_ratio, 2.0) * 0.04
        return round(base_rate + credit_penalty + leverage_penalty, 4)

    @property
    def monthly_interest_rate(self) -> float:
        return self.annual_interest_rate / 12

    @property
    def monthly_payment(self) -> Money:
        if self.principal <= 0 or self.remaining_term_months is None or self.remaining_term_months <= 0:
            return 0
        if self.monthly_interest_rate == 0:
            return round(self.principal / self.remaining_term_months)

        rate = self.monthly_interest_rate
        months = self.remaining_term_months
        payment = self.principal * (rate * ((1 + rate) ** months)) / (((1 + rate) ** months) - 1)
        return max(1, round(payment))

    def apply_monthly_payment(self) -> Money:
        if self.principal <= 0 or self.remaining_term_months is None or self.remaining_term_months <= 0:
            return 0

        interest = round(self.principal * self.monthly_interest_rate)
        principal_payment = max(1, min(self.principal, self.monthly_payment - interest))
        total_payment = interest + principal_payment
        self.principal -= principal_payment
        self.remaining_term_months = max(0, self.remaining_term_months - 1)
        if self.remaining_term_months == 0:
            total_payment += self.principal
            self.principal = 0
        return total_payment

    @property
    def total_interest_estimate(self) -> Money:
        years = self.term_months / 12
        return round(self.principal * self.annual_interest_rate * years)

    @property
    def total_repayment_estimate(self) -> Money:
        return self.principal + self.total_interest_estimate

    def to_dict(self) -> dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "principal": self.principal,
            "annual_interest_rate": self.annual_interest_rate,
            "term_months": self.term_months,
            "credit_rating": self.credit_rating.to_dict(),
            "leverage_ratio": self.leverage_ratio,
            "remaining_term_months": self.remaining_term_months,
            "original_principal": self.original_principal,
            "name": self.name,
            "secured_asset_id": self.secured_asset_id,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Loan:
        return cls(
            loan_id=str(data["loan_id"]),
            principal=int(data["principal"]),
            annual_interest_rate=float(data["annual_interest_rate"]),
            term_months=int(data["term_months"]),
            credit_rating=CreditRating.from_dict(data["credit_rating"]),
            leverage_ratio=float(data["leverage_ratio"]),
            remaining_term_months=int(data.get("remaining_term_months", data["term_months"])),
            original_principal=int(data.get("original_principal", data["principal"])),
            name=str(data.get("name", "Property Loan")),
            secured_asset_id=data.get("secured_asset_id"),
            status=str(data.get("status", "Current")),
        )
