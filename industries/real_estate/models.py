# industries/real_estate/models.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from world.models import City


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _validate_non_negative(name: str, value: int | float) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _validate_ratio(name: str, value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class BuildingType:
    building_type_id: str
    name: str
    base_construction_cost: int
    base_monthly_rent: int
    base_monthly_maintenance: int
    base_property_value: int
    tenant_capacity: int
    target_occupancy: float

    def __post_init__(self) -> None:
        for field_name in (
            "base_construction_cost",
            "base_monthly_rent",
            "base_monthly_maintenance",
            "base_property_value",
        ):
            _validate_non_negative(field_name, getattr(self, field_name))
        if self.tenant_capacity < 1:
            raise ValueError("tenant_capacity must be at least 1.")
        _validate_ratio("target_occupancy", self.target_occupancy)

    def city_construction_cost(self, city: City) -> int:
        return round(self.base_construction_cost * city.property_multiplier)

    def city_monthly_rent(self, city: City) -> int:
        demand_multiplier = 0.75 + (city.demand_score / 200)
        return round(self.base_monthly_rent * city.property_multiplier * demand_multiplier)

    def city_monthly_maintenance(self, city: City) -> int:
        maintenance_multiplier = 0.85 + (city.property_multiplier * 0.15)
        return round(self.base_monthly_maintenance * maintenance_multiplier)

    def city_property_value(self, city: City) -> int:
        demand_multiplier = 0.8 + (city.demand_score / 250)
        return round(self.base_property_value * city.property_multiplier * demand_multiplier)

    def to_dict(self) -> dict[str, Any]:
        return {
            "building_type_id": self.building_type_id,
            "name": self.name,
            "base_construction_cost": self.base_construction_cost,
            "base_monthly_rent": self.base_monthly_rent,
            "base_monthly_maintenance": self.base_monthly_maintenance,
            "base_property_value": self.base_property_value,
            "tenant_capacity": self.tenant_capacity,
            "target_occupancy": self.target_occupancy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuildingType:
        return cls(
            building_type_id=str(data["building_type_id"]),
            name=str(data["name"]),
            base_construction_cost=int(data["base_construction_cost"]),
            base_monthly_rent=int(data["base_monthly_rent"]),
            base_monthly_maintenance=int(data["base_monthly_maintenance"]),
            base_property_value=int(data["base_property_value"]),
            tenant_capacity=int(data["tenant_capacity"]),
            target_occupancy=float(data["target_occupancy"]),
        )


@dataclass(slots=True)
class Tenant:
    name: str
    monthly_rent: int
    tenant_id: str = field(default_factory=lambda: _new_id("tenant"))
    reliability: float = 0.9

    def __post_init__(self) -> None:
        _validate_non_negative("monthly_rent", self.monthly_rent)
        _validate_ratio("reliability", self.reliability)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "monthly_rent": self.monthly_rent,
            "reliability": self.reliability,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tenant:
        return cls(
            tenant_id=str(data["tenant_id"]),
            name=str(data["name"]),
            monthly_rent=int(data["monthly_rent"]),
            reliability=float(data.get("reliability", 0.9)),
        )


@dataclass(frozen=True, slots=True)
class Occupancy:
    occupied_units: int
    total_units: int

    def __post_init__(self) -> None:
        if self.total_units < 1:
            raise ValueError("total_units must be at least 1.")
        if not 0 <= self.occupied_units <= self.total_units:
            raise ValueError("occupied_units must be between 0 and total_units.")

    @property
    def rate(self) -> float:
        return self.occupied_units / self.total_units


@dataclass(slots=True)
class Property:
    name: str
    building_type: BuildingType
    city_id: str
    property_id: str = field(default_factory=lambda: _new_id("property"))
    tenants: list[Tenant] = field(default_factory=list)
    condition: float = 1.0
    property_type: str | None = None
    zoning: str | None = None
    size_sqm: int = 0
    purchase_price: int = 0
    expected_occupancy: float | None = None
    actual_occupancy: float | None = None
    monthly_revenue_override: int | None = None
    monthly_expenses_override: int | None = None

    def __post_init__(self) -> None:
        _validate_ratio("condition", self.condition)
        _validate_non_negative("size_sqm", self.size_sqm)
        _validate_non_negative("purchase_price", self.purchase_price)
        if self.expected_occupancy is not None:
            _validate_ratio("expected_occupancy", self.expected_occupancy)
        if self.actual_occupancy is not None:
            _validate_ratio("actual_occupancy", self.actual_occupancy)
        if self.monthly_revenue_override is not None:
            _validate_non_negative("monthly_revenue_override", self.monthly_revenue_override)
        if self.monthly_expenses_override is not None:
            _validate_non_negative("monthly_expenses_override", self.monthly_expenses_override)
        if len(self.tenants) > self.building_type.tenant_capacity:
            raise ValueError("Property has more tenants than capacity.")

    @property
    def occupancy(self) -> Occupancy:
        if self.actual_occupancy is not None:
            return Occupancy(
                occupied_units=round(self.building_type.tenant_capacity * self.actual_occupancy),
                total_units=self.building_type.tenant_capacity,
            )
        return Occupancy(
            occupied_units=len(self.tenants),
            total_units=self.building_type.tenant_capacity,
        )

    def add_tenant(self, tenant: Tenant) -> None:
        if len(self.tenants) >= self.building_type.tenant_capacity:
            raise ValueError("Property is fully occupied.")
        if self.get_tenant(tenant.tenant_id) is not None:
            raise ValueError(f"Tenant already exists: {tenant.tenant_id}")

        self.tenants.append(tenant)

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return next((tenant for tenant in self.tenants if tenant.tenant_id == tenant_id), None)

    def monthly_rent(self, city: City) -> int:
        if self.monthly_revenue_override is not None:
            if self.actual_occupancy is not None and self.expected_occupancy:
                occupancy_multiplier = self.actual_occupancy / max(self.expected_occupancy, 0.35)
                return round(self.monthly_revenue_override * occupancy_multiplier)
            return self.monthly_revenue_override
        configured_market_rent = self.building_type.city_monthly_rent(city)
        actual_rent = sum(tenant.monthly_rent for tenant in self.tenants)
        return max(actual_rent, round(configured_market_rent * self.occupancy.rate))

    def monthly_maintenance(self, city: City) -> int:
        if self.monthly_expenses_override is not None:
            return self.monthly_expenses_override
        condition_penalty = 1 + ((1 - self.condition) * 0.6)
        return round(self.building_type.city_monthly_maintenance(city) * condition_penalty)

    def property_value(self, city: City) -> int:
        if self.purchase_price:
            occupancy_factor = 0.88 + (self.occupancy.rate * 0.12)
            return round(self.purchase_price * occupancy_factor * self.condition)
        occupancy_factor = 0.75 + (self.occupancy.rate * 0.25)
        return round(self.building_type.city_property_value(city) * occupancy_factor * self.condition)

    def monthly_net_income(self, city: City) -> int:
        return self.monthly_rent(city) - self.monthly_maintenance(city)

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            "name": self.name,
            "building_type_id": self.building_type.building_type_id,
            "city_id": self.city_id,
            "tenants": [tenant.to_dict() for tenant in self.tenants],
            "condition": self.condition,
            "property_type": self.property_type,
            "zoning": self.zoning,
            "size_sqm": self.size_sqm,
            "purchase_price": self.purchase_price,
            "expected_occupancy": self.expected_occupancy,
            "actual_occupancy": self.actual_occupancy,
            "monthly_revenue_override": self.monthly_revenue_override,
            "monthly_expenses_override": self.monthly_expenses_override,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        building_types: dict[str, BuildingType],
    ) -> Property:
        building_type_id = str(data["building_type_id"])
        return cls(
            property_id=str(data["property_id"]),
            name=str(data["name"]),
            building_type=building_types[building_type_id],
            city_id=str(data["city_id"]),
            tenants=[Tenant.from_dict(tenant) for tenant in data.get("tenants", [])],
            condition=float(data.get("condition", 1.0)),
            property_type=data.get("property_type"),
            zoning=data.get("zoning"),
            size_sqm=int(data.get("size_sqm", 0)),
            purchase_price=int(data.get("purchase_price", 0)),
            expected_occupancy=(
                float(data["expected_occupancy"])
                if data.get("expected_occupancy") is not None
                else None
            ),
            actual_occupancy=(
                float(data["actual_occupancy"])
                if data.get("actual_occupancy") is not None
                else None
            ),
            monthly_revenue_override=(
                int(data["monthly_revenue_override"])
                if data.get("monthly_revenue_override") is not None
                else None
            ),
            monthly_expenses_override=(
                int(data["monthly_expenses_override"])
                if data.get("monthly_expenses_override") is not None
                else None
            ),
        )
