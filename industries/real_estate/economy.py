# industries/real_estate/economy.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from importlib.resources import files
from random import Random
from typing import Any
from uuid import uuid4

from finance.models import Loan
from world.models import City


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _validate_non_negative(name: str, value: int | float) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _validate_ratio(name: str, value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1.")


class Zoning(Enum):
    RESIDENTIAL = "Residential"
    OFFICE = "Office"
    COMMERCIAL = "Commercial"
    INDUSTRIAL = "Industrial"
    HOTEL = "Hotel"
    LANDMARK = "Landmark"


class DealRarity(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    LANDMARK = "Landmark"


@dataclass(frozen=True, slots=True)
class DealArchetype:
    archetype_id: str
    property_type: str
    zoning: Zoning
    rarity: DealRarity
    weight: int
    min_size_sqm: int
    max_size_sqm: int
    base_price_per_sqm: int
    base_rent_per_sqm: float
    expense_ratio: float
    min_occupancy: float
    max_occupancy: float
    min_days_remaining: int
    max_days_remaining: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DealArchetype:
        return cls(
            archetype_id=str(data["archetype_id"]),
            property_type=str(data["property_type"]),
            zoning=Zoning(str(data["zoning"])),
            rarity=DealRarity(str(data["rarity"])),
            weight=int(data["weight"]),
            min_size_sqm=int(data["min_size_sqm"]),
            max_size_sqm=int(data["max_size_sqm"]),
            base_price_per_sqm=int(data["base_price_per_sqm"]),
            base_rent_per_sqm=float(data["base_rent_per_sqm"]),
            expense_ratio=float(data["expense_ratio"]),
            min_occupancy=float(data["min_occupancy"]),
            max_occupancy=float(data["max_occupancy"]),
            min_days_remaining=int(data["min_days_remaining"]),
            max_days_remaining=int(data["max_days_remaining"]),
        )


@dataclass(frozen=True, slots=True)
class PropertyListing:
    listing_id: str
    city_id: str
    name: str
    property_type: str
    zoning: Zoning
    rarity: DealRarity
    size_sqm: int
    asking_price: int
    estimated_rent_low: int
    estimated_rent_high: int
    rent_per_sqm: float
    demand_multiplier: float
    occupancy_rate: float
    monthly_revenue: int
    monthly_expenses: int
    days_remaining: int
    condition: float = 0.92
    source_archetype_id: str = ""

    def __post_init__(self) -> None:
        _validate_non_negative("size_sqm", self.size_sqm)
        _validate_non_negative("asking_price", self.asking_price)
        _validate_non_negative("estimated_rent_low", self.estimated_rent_low)
        _validate_non_negative("estimated_rent_high", self.estimated_rent_high)
        _validate_non_negative("rent_per_sqm", self.rent_per_sqm)
        _validate_non_negative("demand_multiplier", self.demand_multiplier)
        _validate_non_negative("monthly_revenue", self.monthly_revenue)
        _validate_non_negative("monthly_expenses", self.monthly_expenses)
        _validate_ratio("occupancy_rate", self.occupancy_rate)
        _validate_ratio("condition", self.condition)
        if self.days_remaining < 1:
            raise ValueError("days_remaining must be at least one.")
        if isinstance(self.zoning, str):
            object.__setattr__(self, "zoning", Zoning(self.zoning))
        if isinstance(self.rarity, str):
            object.__setattr__(self, "rarity", DealRarity(self.rarity))

    @property
    def monthly_profit(self) -> int:
        return self.monthly_revenue - self.monthly_expenses

    @property
    def annual_yield(self) -> float:
        if self.asking_price <= 0:
            return 0.0
        return (self.monthly_profit * 12) / self.asking_price


@dataclass(frozen=True, slots=True)
class LandListing:
    listing_id: str
    city_id: str
    name: str
    asking_price: int
    size_sqm: int
    zoning: Zoning
    demand_multiplier: float
    days_remaining: int

    def __post_init__(self) -> None:
        _validate_non_negative("asking_price", self.asking_price)
        _validate_non_negative("size_sqm", self.size_sqm)
        _validate_non_negative("demand_multiplier", self.demand_multiplier)
        if self.days_remaining < 1:
            raise ValueError("days_remaining must be at least one.")
        if isinstance(self.zoning, str):
            object.__setattr__(self, "zoning", Zoning(self.zoning))


@dataclass(slots=True)
class LandParcel:
    name: str
    city_id: str
    purchase_price: int
    size_sqm: int
    zoning: Zoning | str
    demand_multiplier: float
    parcel_id: str = field(default_factory=lambda: _new_id("land"))
    developed: bool = False

    def __post_init__(self) -> None:
        _validate_non_negative("purchase_price", self.purchase_price)
        _validate_non_negative("size_sqm", self.size_sqm)
        _validate_non_negative("demand_multiplier", self.demand_multiplier)
        if isinstance(self.zoning, str):
            self.zoning = Zoning(self.zoning)

    def to_dict(self) -> dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "name": self.name,
            "city_id": self.city_id,
            "purchase_price": self.purchase_price,
            "size_sqm": self.size_sqm,
            "zoning": self.zoning.value,
            "demand_multiplier": self.demand_multiplier,
            "developed": self.developed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LandParcel:
        size_sqm = data.get("size_sqm")
        if size_sqm is None:
            size_sqm = round(float(data.get("acreage", 0.0)) * 4046.86)
        return cls(
            parcel_id=str(data["parcel_id"]),
            name=str(data["name"]),
            city_id=str(data["city_id"]),
            purchase_price=int(data["purchase_price"]),
            size_sqm=int(size_sqm),
            zoning=str(data["zoning"]),
            demand_multiplier=float(data.get("demand_multiplier", data.get("development_multiplier", 1.0))),
            developed=bool(data.get("developed", False)),
        )


@dataclass(frozen=True, slots=True)
class DevelopmentOption:
    option_id: str
    name: str
    zoning: Zoning
    construction_cost_per_sqm: int
    rent_per_sqm: float
    maintenance_ratio: float
    unit_density_per_1000_sqm: float
    base_build_days: int
    planning_required: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DevelopmentOption:
        return cls(
            option_id=str(data["option_id"]),
            name=str(data["name"]),
            zoning=Zoning(str(data["zoning"])),
            construction_cost_per_sqm=int(data["construction_cost_per_sqm"]),
            rent_per_sqm=float(data["rent_per_sqm"]),
            maintenance_ratio=float(data["maintenance_ratio"]),
            unit_density_per_1000_sqm=float(data["unit_density_per_1000_sqm"]),
            base_build_days=int(data["base_build_days"]),
            planning_required=bool(data.get("planning_required", False)),
        )


@dataclass(frozen=True, slots=True)
class ConstructionCompany:
    company_id: str
    name: str
    cost_multiplier: float
    speed_multiplier: float
    reliability: float
    risk_profile: str
    overrun_chance: float
    delay_chance: float

    def __post_init__(self) -> None:
        _validate_non_negative("cost_multiplier", self.cost_multiplier)
        _validate_non_negative("speed_multiplier", self.speed_multiplier)
        _validate_ratio("reliability", self.reliability)
        _validate_ratio("overrun_chance", self.overrun_chance)
        _validate_ratio("delay_chance", self.delay_chance)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstructionCompany:
        return cls(
            company_id=str(data["company_id"]),
            name=str(data["name"]),
            cost_multiplier=float(data["cost_multiplier"]),
            speed_multiplier=float(data["speed_multiplier"]),
            reliability=float(data["reliability"]),
            risk_profile=str(data["risk_profile"]),
            overrun_chance=float(data["overrun_chance"]),
            delay_chance=float(data["delay_chance"]),
        )


@dataclass(slots=True)
class DevelopmentProject:
    parcel_id: str
    city_id: str
    option_id: str
    building_name: str
    zoning: Zoning | str
    construction_company_id: str
    total_cost: int
    total_days: int
    days_remaining: int
    size_sqm: int
    expected_monthly_rent: int
    expected_monthly_maintenance: int
    unit_count: int
    project_id: str = field(default_factory=lambda: _new_id("development"))

    def __post_init__(self) -> None:
        _validate_non_negative("total_cost", self.total_cost)
        _validate_non_negative("size_sqm", self.size_sqm)
        _validate_non_negative("expected_monthly_rent", self.expected_monthly_rent)
        _validate_non_negative("expected_monthly_maintenance", self.expected_monthly_maintenance)
        if self.total_days < 1:
            raise ValueError("total_days must be at least one.")
        if not 0 <= self.days_remaining <= self.total_days:
            raise ValueError("days_remaining must be between zero and total_days.")
        if isinstance(self.zoning, str):
            self.zoning = Zoning(self.zoning)

    @property
    def complete(self) -> bool:
        return self.days_remaining <= 0

    @property
    def progress(self) -> float:
        return 1 - (self.days_remaining / self.total_days)

    def advance_day(self) -> None:
        self.days_remaining = max(0, self.days_remaining - 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "parcel_id": self.parcel_id,
            "city_id": self.city_id,
            "option_id": self.option_id,
            "building_name": self.building_name,
            "zoning": self.zoning.value,
            "construction_company_id": self.construction_company_id,
            "total_cost": self.total_cost,
            "total_days": self.total_days,
            "days_remaining": self.days_remaining,
            "size_sqm": self.size_sqm,
            "expected_monthly_rent": self.expected_monthly_rent,
            "expected_monthly_maintenance": self.expected_monthly_maintenance,
            "unit_count": self.unit_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DevelopmentProject:
        return cls(
            project_id=str(data["project_id"]),
            parcel_id=str(data["parcel_id"]),
            city_id=str(data["city_id"]),
            option_id=str(data.get("option_id", data.get("building_type_id", "small_office_building"))),
            building_name=str(data["building_name"]),
            zoning=str(data.get("zoning", Zoning.OFFICE.value)),
            construction_company_id=str(data["construction_company_id"]),
            total_cost=int(data["total_cost"]),
            total_days=int(data["total_days"]),
            days_remaining=int(data["days_remaining"]),
            size_sqm=int(data.get("size_sqm", 1000)),
            expected_monthly_rent=int(data.get("expected_monthly_rent", 0)),
            expected_monthly_maintenance=int(data.get("expected_monthly_maintenance", 0)),
            unit_count=int(data.get("unit_count", 1)),
        )


@dataclass(frozen=True, slots=True)
class LoanApproval:
    approved: bool
    reason: str
    max_loan_amount: int
    requested_loan_amount: int
    interest_rate: float
    term_months: int
    monthly_repayment: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PurchaseQuote:
    listing_id: str
    purchase_price: int
    deposit_percent: float
    deposit_amount: int
    loan_amount: int
    taxes_and_fees: int
    cash_required: int
    approval: LoanApproval
    loan: Loan | None = None


@dataclass(frozen=True, slots=True)
class EconomyConfig:
    deal_min_per_city: int
    deal_max_per_city: int
    land_min_per_city: int
    land_max_per_city: int
    stamp_duty_rate: float
    property_tax_annual_rate: float
    corporate_tax_rate: float
    capital_gains_tax_rate: float
    minimum_deposit_percent: float
    max_ltv: float
    max_debt_to_assets: float
    min_credit_score: int
    max_payment_to_profit: float
    base_interest_rate: float
    planning_size_thresholds: dict[Zoning, int]
    planning_base_approval_score: int
    planning_reputation_weight: float
    planning_demand_weight: float
    planning_size_penalty_per_10000_sqm: float
    archetypes: tuple[DealArchetype, ...]
    development_options: tuple[DevelopmentOption, ...]
    construction_companies: tuple[ConstructionCompany, ...]


def load_economy_config() -> EconomyConfig:
    resource = files("industries.real_estate").joinpath("economy_config.json")
    data = json.loads(resource.read_text(encoding="utf-8"))
    deal_generation = data["deal_generation"]
    land_generation = data["land_generation"]
    taxes = data["tax_rates"]
    loan = data["loan_settings"]
    planning = data["planning_settings"]
    return EconomyConfig(
        deal_min_per_city=int(deal_generation["min_per_city"]),
        deal_max_per_city=int(deal_generation["max_per_city"]),
        land_min_per_city=int(land_generation["min_per_city"]),
        land_max_per_city=int(land_generation["max_per_city"]),
        stamp_duty_rate=float(taxes["stamp_duty_rate"]),
        property_tax_annual_rate=float(taxes["property_tax_annual_rate"]),
        corporate_tax_rate=float(taxes["corporate_tax_rate"]),
        capital_gains_tax_rate=float(taxes["capital_gains_tax_rate"]),
        minimum_deposit_percent=float(loan["minimum_deposit_percent"]),
        max_ltv=float(loan["max_ltv"]),
        max_debt_to_assets=float(loan["max_debt_to_assets"]),
        min_credit_score=int(loan["min_credit_score"]),
        max_payment_to_profit=float(loan["max_payment_to_profit"]),
        base_interest_rate=float(loan["base_interest_rate"]),
        planning_size_thresholds={
            Zoning.RESIDENTIAL: int(planning["residential_threshold_sqm"]),
            Zoning.OFFICE: int(planning["office_threshold_sqm"]),
            Zoning.COMMERCIAL: int(planning["commercial_threshold_sqm"]),
            Zoning.INDUSTRIAL: int(planning["industrial_threshold_sqm"]),
        },
        planning_base_approval_score=int(planning["base_approval_score"]),
        planning_reputation_weight=float(planning["reputation_weight"]),
        planning_demand_weight=float(planning["demand_weight"]),
        planning_size_penalty_per_10000_sqm=float(planning["size_penalty_per_10000_sqm"]),
        archetypes=tuple(DealArchetype.from_dict(item) for item in data["deal_archetypes"]),
        development_options=tuple(DevelopmentOption.from_dict(item) for item in data["development_options"]),
        construction_companies=tuple(
            ConstructionCompany.from_dict(item) for item in data["construction_companies"]
        ),
    )


class PropertyMarketplace:
    def __init__(self, config: EconomyConfig | None = None) -> None:
        self._config = config or load_economy_config()

    def active_listings(self, city: City) -> tuple[PropertyListing, ...]:
        random = Random(f"property-market-v2:{city.city_id}")
        count = random.randint(self._config.deal_min_per_city, self._config.deal_max_per_city)
        listings: list[PropertyListing] = []
        for index in range(count):
            archetype = self._weighted_archetype(random)
            size_sqm = random.randint(archetype.min_size_sqm, archetype.max_size_sqm)
            demand_multiplier = round(0.75 + (city.demand_score / 100) * 0.55, 3)
            occupancy = round(random.uniform(archetype.min_occupancy, archetype.max_occupancy), 3)
            price_variation = random.uniform(0.88, 1.16)
            rent_variation = random.uniform(0.92, 1.12)
            asking_price = round(
                size_sqm * archetype.base_price_per_sqm * city.property_multiplier * demand_multiplier * price_variation
            )
            rent_per_sqm = round(archetype.base_rent_per_sqm * city.property_multiplier * demand_multiplier * rent_variation, 2)
            monthly_revenue = round(size_sqm * rent_per_sqm * occupancy)
            monthly_expenses = round(monthly_revenue * archetype.expense_ratio)
            rent_low = round(monthly_revenue * 0.9)
            rent_high = round(monthly_revenue * 1.08)
            days_remaining = random.randint(archetype.min_days_remaining, archetype.max_days_remaining)
            listings.append(
                PropertyListing(
                    listing_id=f"{city.city_id}_deal_{index + 1:02d}",
                    city_id=city.city_id,
                    name=f"{city.name} {archetype.property_type} {index + 1}",
                    property_type=archetype.property_type,
                    zoning=archetype.zoning,
                    rarity=archetype.rarity,
                    size_sqm=size_sqm,
                    asking_price=asking_price,
                    estimated_rent_low=rent_low,
                    estimated_rent_high=rent_high,
                    rent_per_sqm=rent_per_sqm,
                    demand_multiplier=demand_multiplier,
                    occupancy_rate=occupancy,
                    monthly_revenue=monthly_revenue,
                    monthly_expenses=monthly_expenses,
                    days_remaining=days_remaining,
                    condition=round(random.uniform(0.72, 1.0), 3),
                    source_archetype_id=archetype.archetype_id,
                )
            )
        return tuple(listings)

    def get_listing(self, city: City, listing_id: str) -> PropertyListing | None:
        return next((listing for listing in self.active_listings(city) if listing.listing_id == listing_id), None)

    def _weighted_archetype(self, random: Random) -> DealArchetype:
        weighted: list[DealArchetype] = []
        for archetype in self._config.archetypes:
            weighted.extend([archetype] * archetype.weight)
        return random.choice(weighted)


class LandMarketplace:
    def __init__(self, config: EconomyConfig | None = None) -> None:
        self._config = config or load_economy_config()

    def active_listings(self, city: City) -> tuple[LandListing, ...]:
        random = Random(f"land-market-v2:{city.city_id}")
        count = random.randint(self._config.land_min_per_city, self._config.land_max_per_city)
        listings: list[LandListing] = []
        zoning_options = (Zoning.RESIDENTIAL, Zoning.OFFICE, Zoning.COMMERCIAL, Zoning.INDUSTRIAL)
        for index in range(count):
            size_sqm = random.randint(800, 42000)
            demand_multiplier = round(0.72 + (city.demand_score / 100) * 0.5 + random.uniform(-0.08, 0.08), 3)
            zoning = random.choice(zoning_options)
            zoning_factor = {
                Zoning.RESIDENTIAL: 0.9,
                Zoning.OFFICE: 1.1,
                Zoning.COMMERCIAL: 1.0,
                Zoning.INDUSTRIAL: 0.74,
            }[zoning]
            asking_price = round(size_sqm * 145 * city.property_multiplier * demand_multiplier * zoning_factor)
            listings.append(
                LandListing(
                    listing_id=f"{city.city_id}_land_{index + 1:02d}",
                    city_id=city.city_id,
                    name=f"{city.name} {zoning.value} Site {index + 1}",
                    asking_price=asking_price,
                    size_sqm=size_sqm,
                    zoning=zoning,
                    demand_multiplier=demand_multiplier,
                    days_remaining=random.randint(20, 180),
                )
            )
        return tuple(listings)

    def get_listing(self, city: City, listing_id: str) -> LandListing | None:
        return next((listing for listing in self.active_listings(city) if listing.listing_id == listing_id), None)


def default_construction_companies() -> tuple[ConstructionCompany, ...]:
    return load_economy_config().construction_companies


def default_development_options() -> tuple[DevelopmentOption, ...]:
    return load_economy_config().development_options
