# gameplay/models.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ResearchEffect:
    key: str
    amount: float
    label: str


@dataclass(frozen=True, slots=True)
class CityManagerProfile:
    manager_id: str
    name: str
    city_id: str
    monthly_budget: int
    min_yield: float
    max_property_price: int
    allowed_property_types: tuple[str, ...]
    aggressiveness: str
    cash_reserve_requirement: int
    properties_purchased: int = 0
    capital_invested: int = 0
    yield_achieved_sum: float = 0.0
    status: str = "Active"
    month_spent: int = 0
    budget_month: str = ""

    @property
    def average_yield_achieved(self) -> float:
        if self.properties_purchased <= 0:
            return 0.0
        return self.yield_achieved_sum / self.properties_purchased

    def to_dict(self) -> dict[str, Any]:
        return {
            "manager_id": self.manager_id,
            "name": self.name,
            "city_id": self.city_id,
            "monthly_budget": self.monthly_budget,
            "min_yield": self.min_yield,
            "max_property_price": self.max_property_price,
            "allowed_property_types": list(self.allowed_property_types),
            "aggressiveness": self.aggressiveness,
            "cash_reserve_requirement": self.cash_reserve_requirement,
            "properties_purchased": self.properties_purchased,
            "capital_invested": self.capital_invested,
            "yield_achieved_sum": self.yield_achieved_sum,
            "status": self.status,
            "month_spent": self.month_spent,
            "budget_month": self.budget_month,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CityManagerProfile:
        return cls(
            manager_id=str(data["manager_id"]),
            name=str(data["name"]),
            city_id=str(data["city_id"]),
            monthly_budget=int(data["monthly_budget"]),
            min_yield=float(data["min_yield"]),
            max_property_price=int(data["max_property_price"]),
            allowed_property_types=tuple(str(item) for item in data.get("allowed_property_types", ())),
            aggressiveness=str(data.get("aggressiveness", "Balanced")),
            cash_reserve_requirement=int(data.get("cash_reserve_requirement", 0)),
            properties_purchased=int(data.get("properties_purchased", 0)),
            capital_invested=int(data.get("capital_invested", 0)),
            yield_achieved_sum=float(data.get("yield_achieved_sum", 0.0)),
            status=str(data.get("status", "Active")),
            month_spent=int(data.get("month_spent", 0)),
            budget_month=str(data.get("budget_month", "")),
        )


@dataclass(frozen=True, slots=True)
class MegaProjectOpportunity:
    project_id: str
    name: str
    city_id: str
    project_type: str
    estimated_cost: int
    construction_days: int
    expected_revenue: int
    expected_profit: int
    risk_rating: str
    prestige_reward: int
    status: str = "Available"
    days_remaining: int = 540

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "city_id": self.city_id,
            "project_type": self.project_type,
            "estimated_cost": self.estimated_cost,
            "construction_days": self.construction_days,
            "expected_revenue": self.expected_revenue,
            "expected_profit": self.expected_profit,
            "risk_rating": self.risk_rating,
            "prestige_reward": self.prestige_reward,
            "status": self.status,
            "days_remaining": self.days_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MegaProjectOpportunity:
        return cls(
            project_id=str(data["project_id"]),
            name=str(data["name"]),
            city_id=str(data["city_id"]),
            project_type=str(data["project_type"]),
            estimated_cost=int(data["estimated_cost"]),
            construction_days=int(data["construction_days"]),
            expected_revenue=int(data["expected_revenue"]),
            expected_profit=int(data["expected_profit"]),
            risk_rating=str(data["risk_rating"]),
            prestige_reward=int(data["prestige_reward"]),
            status=str(data.get("status", "Available")),
            days_remaining=int(data.get("days_remaining", 540)),
        )
