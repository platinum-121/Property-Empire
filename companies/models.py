# companies/models.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from finance.models import BalanceSheet, CreditRating, Loan


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _validate_reputation(reputation: float) -> None:
    if not 0 <= reputation <= 100:
        raise ValueError("Reputation must be between 0 and 100.")


def _validate_cash(cash: int) -> None:
    if cash < 0:
        raise ValueError("Cash cannot be negative.")


def _validate_count(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _validate_price(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _validate_percent(name: str, value: float) -> None:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100.")


@dataclass(frozen=True, slots=True)
class SkillRatings:
    leadership: float = 50.0
    finance: float = 50.0
    operations: float = 50.0
    negotiation: float = 50.0
    innovation: float = 50.0
    people: float = 50.0

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            _validate_percent(name, value)

    @property
    def average(self) -> float:
        values = self.to_dict().values()
        return sum(values) / len(self.to_dict())

    def boost_values(self, workload_percent: float, loyalty: float) -> dict[str, float]:
        workload_factor = workload_percent / 100
        loyalty_factor = 0.75 + (loyalty / 400)
        return {
            "leadership": round((self.leadership / 100) * workload_factor * loyalty_factor, 4),
            "finance": round((self.finance / 100) * workload_factor * loyalty_factor, 4),
            "operations": round((self.operations / 100) * workload_factor * loyalty_factor, 4),
            "negotiation": round((self.negotiation / 100) * workload_factor * loyalty_factor, 4),
            "innovation": round((self.innovation / 100) * workload_factor * loyalty_factor, 4),
            "people": round((self.people / 100) * workload_factor * loyalty_factor, 4),
        }

    def to_dict(self) -> dict[str, float]:
        return {
            "leadership": self.leadership,
            "finance": self.finance,
            "operations": self.operations,
            "negotiation": self.negotiation,
            "innovation": self.innovation,
            "people": self.people,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SkillRatings:
        if data is None:
            return cls()

        return cls(
            leadership=float(data.get("leadership", 50.0)),
            finance=float(data.get("finance", 50.0)),
            operations=float(data.get("operations", 50.0)),
            negotiation=float(data.get("negotiation", 50.0)),
            innovation=float(data.get("innovation", 50.0)),
            people=float(data.get("people", 50.0)),
        )


@dataclass(slots=True)
class StaffMember:
    name: str
    title: str
    staff_id: str
    skills: SkillRatings = field(default_factory=SkillRatings)
    salary: int = 0
    loyalty: float = 50.0
    traits: tuple[str, ...] = field(default_factory=tuple)
    workload_percent: float = 100.0
    reputation: float = 50.0

    def __post_init__(self) -> None:
        _validate_cash(self.salary)
        _validate_percent("loyalty", self.loyalty)
        _validate_percent("workload_percent", self.workload_percent)
        _validate_reputation(self.reputation)
        self.traits = tuple(self.traits)

    @property
    def retention_score(self) -> float:
        return round((self.loyalty * 0.7) + (self.reputation * 0.3), 2)

    @property
    def poaching_cost(self) -> int:
        if self.salary <= 0:
            return 0

        loyalty_multiplier = 1 + (self.loyalty / 100)
        reputation_multiplier = 1 + (self.reputation / 200)
        return round(self.salary * 2 * loyalty_multiplier * reputation_multiplier)

    def set_workload(self, workload_percent: float) -> None:
        _validate_percent("workload_percent", workload_percent)
        self.workload_percent = workload_percent

    def set_loyalty(self, loyalty: float) -> None:
        _validate_percent("loyalty", loyalty)
        self.loyalty = loyalty

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "staff_id": self.staff_id,
            "skills": self.skills.to_dict(),
            "salary": self.salary,
            "loyalty": self.loyalty,
            "traits": list(self.traits),
            "workload_percent": self.workload_percent,
            "reputation": self.reputation,
        }


@dataclass(slots=True)
class Executive(StaffMember):
    executive_id: str = field(default_factory=lambda: _new_id("executive"))

    def __init__(
        self,
        name: str,
        title: str,
        reputation: float = 50.0,
        executive_id: str | None = None,
        skills: SkillRatings | None = None,
        salary: int = 0,
        loyalty: float = 50.0,
        traits: tuple[str, ...] = (),
        workload_percent: float = 100.0,
    ) -> None:
        StaffMember.__init__(
            self,
            name=name,
            title=title,
            staff_id=executive_id or _new_id("executive"),
            skills=skills or SkillRatings(),
            salary=salary,
            loyalty=loyalty,
            traits=traits,
            workload_percent=workload_percent,
            reputation=reputation,
        )
        self.executive_id = self.staff_id

    def company_boosts(self) -> dict[str, float]:
        boosts = self.skills.boost_values(
            workload_percent=self.workload_percent,
            loyalty=self.loyalty,
        )
        return {
            "reputation": round(boosts["leadership"] * 0.04 + boosts["people"] * 0.02, 4),
            "profit": round(boosts["finance"] * 0.04 + boosts["operations"] * 0.02, 4),
            "operations": round(boosts["operations"] * 0.05 + boosts["leadership"] * 0.015, 4),
            "growth": round(boosts["innovation"] * 0.04 + boosts["negotiation"] * 0.02, 4),
            "deal_quality": round(boosts["negotiation"] * 0.05 + boosts["finance"] * 0.015, 4),
        }

    def to_dict(self) -> dict[str, Any]:
        data = StaffMember.to_dict(self)
        data["executive_id"] = self.executive_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Executive:
        return cls(
            executive_id=str(data.get("executive_id", data.get("staff_id", _new_id("executive")))),
            name=str(data["name"]),
            title=str(data["title"]),
            reputation=float(data.get("reputation", 50.0)),
            skills=SkillRatings.from_dict(data.get("skills")),
            salary=int(data.get("salary", 0)),
            loyalty=float(data.get("loyalty", 50.0)),
            traits=tuple(data.get("traits", ())),
            workload_percent=float(data.get("workload_percent", 100.0)),
        )


class ManagementRole(Enum):
    BRANCH_MANAGER = "branch_manager"
    REGIONAL_MANAGER = "regional_manager"
    COUNTRY_MANAGER = "country_manager"
    CONTINENTAL_DIRECTOR = "continental_director"


@dataclass(slots=True)
class Manager(StaffMember):
    manager_id: str = field(default_factory=lambda: _new_id("manager"))
    role: ManagementRole = ManagementRole.BRANCH_MANAGER
    city_id: str | None = None
    region_id: str | None = None
    country_id: str | None = None
    continent_id: str | None = None

    def __init__(
        self,
        name: str,
        title: str,
        reputation: float = 50.0,
        manager_id: str | None = None,
        skills: SkillRatings | None = None,
        salary: int = 0,
        loyalty: float = 50.0,
        traits: tuple[str, ...] = (),
        workload_percent: float = 100.0,
        role: ManagementRole | str = ManagementRole.BRANCH_MANAGER,
        city_id: str | None = None,
        region_id: str | None = None,
        country_id: str | None = None,
        continent_id: str | None = None,
    ) -> None:
        StaffMember.__init__(
            self,
            name=name,
            title=title,
            staff_id=manager_id or _new_id("manager"),
            skills=skills or SkillRatings(),
            salary=salary,
            loyalty=loyalty,
            traits=traits,
            workload_percent=workload_percent,
            reputation=reputation,
        )
        self.manager_id = self.staff_id
        self.role = role if isinstance(role, ManagementRole) else ManagementRole(str(role))
        self.city_id = city_id
        self.region_id = region_id
        self.country_id = country_id
        self.continent_id = continent_id

    def department_boosts(self) -> dict[str, float]:
        boosts = self.skills.boost_values(
            workload_percent=self.workload_percent,
            loyalty=self.loyalty,
        )
        return {
            "efficiency": round(boosts["operations"] * 0.04 + boosts["leadership"] * 0.02, 4),
            "morale": round(boosts["people"] * 0.05 + boosts["leadership"] * 0.01, 4),
            "execution": round(boosts["operations"] * 0.03 + boosts["finance"] * 0.015, 4),
        }

    def to_dict(self) -> dict[str, Any]:
        data = StaffMember.to_dict(self)
        data["manager_id"] = self.manager_id
        data["role"] = self.role.value
        data["city_id"] = self.city_id
        data["region_id"] = self.region_id
        data["country_id"] = self.country_id
        data["continent_id"] = self.continent_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Manager:
        title = str(data["title"])
        default_role = ManagementRole.BRANCH_MANAGER
        if "regional" in title.lower():
            default_role = ManagementRole.REGIONAL_MANAGER
        elif "country" in title.lower():
            default_role = ManagementRole.COUNTRY_MANAGER
        elif "continental" in title.lower() or "director" in title.lower():
            default_role = ManagementRole.CONTINENTAL_DIRECTOR
        return cls(
            manager_id=str(data.get("manager_id", data.get("staff_id", _new_id("manager")))),
            name=str(data["name"]),
            title=title,
            reputation=float(data.get("reputation", 50.0)),
            skills=SkillRatings.from_dict(data.get("skills")),
            salary=int(data.get("salary", 0)),
            loyalty=float(data.get("loyalty", 50.0)),
            traits=tuple(data.get("traits", ())),
            workload_percent=float(data.get("workload_percent", 100.0)),
            role=ManagementRole(str(data.get("role", default_role.value))),
            city_id=data.get("city_id"),
            region_id=data.get("region_id"),
            country_id=data.get("country_id"),
            continent_id=data.get("continent_id"),
        )


@dataclass(slots=True)
class Asset:
    name: str
    value: int
    asset_id: str = field(default_factory=lambda: _new_id("asset"))

    def __post_init__(self) -> None:
        _validate_cash(self.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Asset:
        return cls(
            asset_id=str(data["asset_id"]),
            name=str(data["name"]),
            value=int(data["value"]),
        )


class CompanyListingStatus(Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class BranchType(Enum):
    HQ = "hq"
    BRANCH = "branch"
    REGIONAL_OFFICE = "regional_office"


class NPCCompanyTrait(Enum):
    EXPANSIONIST = "expansionist"
    CONSERVATIVE = "conservative"
    ACQUISITION_FOCUSED = "acquisition_focused"
    DIVIDEND_FOCUSED = "dividend_focused"
    EFFICIENCY_FOCUSED = "efficiency_focused"
    ASSET_COLLECTOR = "asset_collector"


@dataclass(slots=True)
class ShareLedger:
    total_shares: int = 0
    player_shares: int = 0
    npc_shareholders: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_count("total_shares", self.total_shares)
        _validate_count("player_shares", self.player_shares)
        self.npc_shareholders = {
            str(shareholder_id): int(share_count)
            for shareholder_id, share_count in self.npc_shareholders.items()
        }
        for shareholder_id, share_count in self.npc_shareholders.items():
            _validate_count(f"npc_shareholders.{shareholder_id}", share_count)
        if self.allocated_shares > self.total_shares:
            raise ValueError("Allocated shares cannot exceed total shares.")

    @property
    def npc_shares(self) -> int:
        return sum(self.npc_shareholders.values())

    @property
    def allocated_shares(self) -> int:
        return self.player_shares + self.npc_shares

    @property
    def unallocated_shares(self) -> int:
        return self.total_shares - self.allocated_shares

    def add_player_shares(self, share_count: int) -> None:
        _validate_count("share_count", share_count)
        if share_count > self.unallocated_shares:
            raise ValueError("Not enough unallocated shares are available.")

        self.player_shares += share_count

    def add_npc_shares(self, shareholder_id: str, share_count: int) -> None:
        _validate_count("share_count", share_count)
        if share_count > self.unallocated_shares:
            raise ValueError("Not enough unallocated shares are available.")

        self.npc_shareholders[shareholder_id] = (
            self.npc_shareholders.get(shareholder_id, 0) + share_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_shares": self.total_shares,
            "player_shares": self.player_shares,
            "npc_shareholders": self.npc_shareholders,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ShareLedger:
        if data is None:
            return cls()

        return cls(
            total_shares=int(data.get("total_shares", 0)),
            player_shares=int(data.get("player_shares", 0)),
            npc_shareholders={
                str(shareholder_id): int(share_count)
                for shareholder_id, share_count in data.get("npc_shareholders", {}).items()
            },
        )


@dataclass(slots=True)
class StockProfile:
    listing_status: CompanyListingStatus = CompanyListingStatus.PRIVATE
    share_price: float = 0.0
    share_ledger: ShareLedger = field(default_factory=ShareLedger)
    dividend_per_share: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.listing_status, str):
            self.listing_status = CompanyListingStatus(self.listing_status)
        _validate_price("share_price", self.share_price)
        _validate_price("dividend_per_share", self.dividend_per_share)
        if self.is_public and self.share_ledger.total_shares <= 0:
            raise ValueError("Public companies must have at least one share.")

    @property
    def is_private(self) -> bool:
        return self.listing_status is CompanyListingStatus.PRIVATE

    @property
    def is_public(self) -> bool:
        return self.listing_status is CompanyListingStatus.PUBLIC

    @property
    def market_cap(self) -> int:
        if self.is_private:
            return 0

        return round(self.share_price * self.share_ledger.total_shares)

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_status": self.listing_status.value,
            "share_price": self.share_price,
            "share_ledger": self.share_ledger.to_dict(),
            "dividend_per_share": self.dividend_per_share,
        }

    @classmethod
    def private(cls) -> StockProfile:
        return cls()

    @classmethod
    def public(
        cls,
        share_price: float,
        total_shares: int,
        player_shares: int = 0,
        npc_shareholders: dict[str, int] | None = None,
    ) -> StockProfile:
        return cls(
            listing_status=CompanyListingStatus.PUBLIC,
            share_price=share_price,
            share_ledger=ShareLedger(
                total_shares=total_shares,
                player_shares=player_shares,
                npc_shareholders=npc_shareholders or {},
            ),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> StockProfile:
        if data is None:
            return cls.private()

        return cls(
            listing_status=CompanyListingStatus(str(data.get("listing_status", "private"))),
            share_price=float(data.get("share_price", 0.0)),
            share_ledger=ShareLedger.from_dict(data.get("share_ledger")),
            dividend_per_share=float(data.get("dividend_per_share", 0.0)),
        )


@dataclass(slots=True)
class Department:
    name: str
    department_id: str = field(default_factory=lambda: _new_id("department"))
    managers: list[Manager] = field(default_factory=list)
    workload_percent: float = 100.0

    def __post_init__(self) -> None:
        _validate_percent("workload_percent", self.workload_percent)

    def add_manager(self, manager: Manager) -> None:
        if self.get_manager(manager.manager_id) is not None:
            raise ValueError(f"Manager already exists: {manager.manager_id}")

        self.managers.append(manager)

    def get_manager(self, manager_id: str) -> Manager | None:
        return next((manager for manager in self.managers if manager.manager_id == manager_id), None)

    def aggregate_manager_boosts(self) -> dict[str, float]:
        totals = {"efficiency": 0.0, "morale": 0.0, "execution": 0.0}
        for manager in self.managers:
            for key, value in manager.department_boosts().items():
                totals[key] += value

        return {key: round(value, 4) for key, value in totals.items()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "department_id": self.department_id,
            "name": self.name,
            "managers": [manager.to_dict() for manager in self.managers],
            "workload_percent": self.workload_percent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Department:
        return cls(
            department_id=str(data["department_id"]),
            name=str(data["name"]),
            managers=[Manager.from_dict(manager) for manager in data.get("managers", [])],
            workload_percent=float(data.get("workload_percent", 100.0)),
        )


@dataclass(slots=True)
class Branch:
    name: str
    branch_id: str = field(default_factory=lambda: _new_id("branch"))
    city_id: str | None = None
    branch_type: BranchType = BranchType.BRANCH
    manager_id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.branch_type, str):
            self.branch_type = BranchType(self.branch_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "name": self.name,
            "city_id": self.city_id,
            "branch_type": self.branch_type.value,
            "manager_id": self.manager_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Branch:
        return cls(
            branch_id=str(data["branch_id"]),
            name=str(data["name"]),
            city_id=data.get("city_id"),
            branch_type=BranchType(str(data.get("branch_type", BranchType.BRANCH.value))),
            manager_id=data.get("manager_id"),
        )


@dataclass(slots=True)
class Division:
    name: str
    division_id: str = field(default_factory=lambda: _new_id("division"))
    branches: list[Branch] = field(default_factory=list)
    departments: list[Department] = field(default_factory=list)

    @property
    def manager_count(self) -> int:
        return sum(len(department.managers) for department in self.departments)

    def add_branch(self, branch: Branch) -> None:
        if self.get_branch(branch.branch_id) is not None:
            raise ValueError(f"Branch already exists: {branch.branch_id}")

        self.branches.append(branch)

    def add_department(self, department: Department) -> None:
        if self.get_department(department.department_id) is not None:
            raise ValueError(f"Department already exists: {department.department_id}")

        self.departments.append(department)

    def get_branch(self, branch_id: str) -> Branch | None:
        return next((branch for branch in self.branches if branch.branch_id == branch_id), None)

    def get_department(self, department_id: str) -> Department | None:
        return next(
            (department for department in self.departments if department.department_id == department_id),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "division_id": self.division_id,
            "name": self.name,
            "branches": [branch.to_dict() for branch in self.branches],
            "departments": [department.to_dict() for department in self.departments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Division:
        return cls(
            division_id=str(data["division_id"]),
            name=str(data["name"]),
            branches=[Branch.from_dict(branch) for branch in data.get("branches", [])],
            departments=[
                Department.from_dict(department) for department in data.get("departments", [])
            ],
        )


@dataclass(slots=True)
class Company:
    name: str
    company_id: str = field(default_factory=lambda: _new_id("company"))
    cash: int = 0
    reputation: float = 50.0
    executives: list[Executive] = field(default_factory=list)
    divisions: list[Division] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    stock_profile: StockProfile = field(default_factory=StockProfile.private)
    loans: list[Loan] = field(default_factory=list)
    npc_traits: tuple[NPCCompanyTrait, ...] = field(default_factory=tuple)
    subsidiaries: list[Company] = field(default_factory=list)
    industry_id: str | None = None

    def __post_init__(self) -> None:
        _validate_cash(self.cash)
        _validate_reputation(self.reputation)
        self.npc_traits = tuple(
            trait if isinstance(trait, NPCCompanyTrait) else NPCCompanyTrait(str(trait))
            for trait in self.npc_traits
        )

    @property
    def branch_count(self) -> int:
        return sum(len(division.branches) for division in self.divisions)

    @property
    def department_count(self) -> int:
        return sum(len(division.departments) for division in self.divisions)

    @property
    def manager_count(self) -> int:
        return sum(division.manager_count for division in self.divisions)

    @property
    def managers(self) -> tuple[Manager, ...]:
        return tuple(
            manager
            for division in self.divisions
            for department in division.departments
            for manager in department.managers
        )

    @property
    def manager_payroll(self) -> int:
        return sum(manager.salary for manager in self.managers)

    @property
    def is_private(self) -> bool:
        return self.stock_profile.is_private

    @property
    def is_public(self) -> bool:
        return self.stock_profile.is_public

    @property
    def share_price(self) -> float:
        return self.stock_profile.share_price

    @property
    def market_cap(self) -> int:
        return self.stock_profile.market_cap

    @property
    def player_share_count(self) -> int:
        return self.stock_profile.share_ledger.player_shares

    @property
    def npc_share_count(self) -> int:
        return self.stock_profile.share_ledger.npc_shares

    @property
    def total_debt(self) -> int:
        return sum(loan.principal for loan in self.loans)

    def add_cash(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cash additions cannot be negative.")

        self.cash += amount

    def spend_cash(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cash spending cannot be negative.")
        if amount > self.cash:
            raise ValueError("Company does not have enough cash.")

        self.cash -= amount

    def set_reputation(self, reputation: float) -> None:
        _validate_reputation(reputation)
        self.reputation = reputation

    def has_npc_trait(self, trait: NPCCompanyTrait) -> bool:
        return trait in self.npc_traits

    def add_npc_trait(self, trait: NPCCompanyTrait) -> None:
        if trait not in self.npc_traits:
            self.npc_traits = (*self.npc_traits, trait)

    def balance_sheet_snapshot(self) -> BalanceSheet:
        asset_value = self.cash + sum(asset.value for asset in self.assets)
        return BalanceSheet(
            assets={"cash_and_assets": asset_value},
            liabilities={"loans": self.total_debt},
        )

    def take_loan(
        self,
        principal: int,
        term_months: int,
        credit_rating: CreditRating | None = None,
        base_rate: float = 0.035,
    ) -> Loan:
        _validate_cash(principal)
        if principal <= 0:
            raise ValueError("Loan principal must be greater than zero.")

        rating = credit_rating or CreditRating(score=round(300 + (self.reputation * 4)))
        loan = Loan.quote(
            principal=principal,
            term_months=term_months,
            credit_rating=rating,
            balance_sheet=self.balance_sheet_snapshot(),
            base_rate=base_rate,
        )
        self.loans.append(loan)
        self.add_cash(principal)
        return loan

    def repay_loan(self, loan_id: str, amount: int) -> Loan | None:
        _validate_cash(amount)
        if amount <= 0:
            raise ValueError("Loan repayment must be greater than zero.")
        if amount > self.cash:
            raise ValueError("Company does not have enough cash for repayment.")

        for index, loan in enumerate(self.loans):
            if loan.loan_id == loan_id:
                repayment = min(amount, loan.principal)
                self.spend_cash(repayment)
                loan.principal -= repayment
                if loan.principal <= 0:
                    self.loans.pop(index)
                    return None

                return loan

        raise ValueError(f"Loan not found: {loan_id}")

    def add_executive(self, executive: Executive) -> None:
        if self.get_executive(executive.executive_id) is not None:
            raise ValueError(f"Executive already exists: {executive.executive_id}")

        self.executives.append(executive)

    def remove_executive(self, executive_id: str) -> Executive:
        for index, executive in enumerate(self.executives):
            if executive.executive_id == executive_id:
                return self.executives.pop(index)

        raise ValueError(f"Executive not found: {executive_id}")

    def get_executive(self, executive_id: str) -> Executive | None:
        return next(
            (executive for executive in self.executives if executive.executive_id == executive_id),
            None,
        )

    def poach_executive_from(
        self,
        source_company: Company,
        executive_id: str,
        signing_bonus: int,
    ) -> Executive:
        if source_company.company_id == self.company_id:
            raise ValueError("A company cannot poach from itself.")
        _validate_cash(signing_bonus)

        executive = source_company.get_executive(executive_id)
        if executive is None:
            raise ValueError(f"Executive not found: {executive_id}")
        if signing_bonus < executive.poaching_cost:
            raise ValueError("Signing bonus is below the executive's poaching cost.")
        if signing_bonus > self.cash:
            raise ValueError("Company does not have enough cash for the signing bonus.")

        self.spend_cash(signing_bonus)
        poached = source_company.remove_executive(executive_id)
        poached.set_loyalty(max(25.0, poached.loyalty - 20.0))
        self.add_executive(poached)
        return poached

    def aggregate_executive_boosts(self) -> dict[str, float]:
        totals = {
            "reputation": 0.0,
            "profit": 0.0,
            "operations": 0.0,
            "growth": 0.0,
            "deal_quality": 0.0,
        }
        for executive in self.executives:
            for key, value in executive.company_boosts().items():
                totals[key] += value

        return {key: round(value, 4) for key, value in totals.items()}

    def add_division(self, division: Division) -> None:
        if self.get_division(division.division_id) is not None:
            raise ValueError(f"Division already exists: {division.division_id}")

        self.divisions.append(division)

    def add_subsidiary(self, company: Company) -> None:
        if company.company_id == self.company_id:
            raise ValueError("A company cannot be its own subsidiary.")
        if self.get_subsidiary(company.company_id) is not None:
            raise ValueError(f"Subsidiary already exists: {company.company_id}")

        self.subsidiaries.append(company)

    def remove_subsidiary(self, company_id: str) -> Company:
        for index, subsidiary in enumerate(self.subsidiaries):
            if subsidiary.company_id == company_id:
                return self.subsidiaries.pop(index)

            try:
                return subsidiary.remove_subsidiary(company_id)
            except ValueError:
                pass

        raise ValueError(f"Subsidiary not found: {company_id}")

    def absorb_subsidiary(self, company_id: str) -> Company:
        subsidiary = self.remove_subsidiary(company_id)
        self.cash += subsidiary.cash
        self.executives.extend(subsidiary.executives)
        self.divisions.extend(subsidiary.divisions)
        self.assets.extend(subsidiary.assets)
        self.subsidiaries.extend(subsidiary.subsidiaries)
        return subsidiary

    def spinoff_subsidiary(self, company_id: str) -> Company:
        return self.remove_subsidiary(company_id)

    def add_asset(self, asset: Asset) -> None:
        if self.get_asset(asset.asset_id) is not None:
            raise ValueError(f"Asset already exists: {asset.asset_id}")

        self.assets.append(asset)

    def get_asset(self, asset_id: str) -> Asset | None:
        return next((asset for asset in self.assets if asset.asset_id == asset_id), None)

    def remove_asset(self, asset_id: str) -> Asset:
        for index, asset in enumerate(self.assets):
            if asset.asset_id == asset_id:
                return self.assets.pop(index)

        raise ValueError(f"Asset not found: {asset_id}")

    def get_division(self, division_id: str) -> Division | None:
        return next((division for division in self.divisions if division.division_id == division_id), None)

    def get_subsidiary(self, company_id: str) -> Company | None:
        for subsidiary in self.subsidiaries:
            if subsidiary.company_id == company_id:
                return subsidiary

            nested = subsidiary.get_subsidiary(company_id)
            if nested is not None:
                return nested

        return None

    def total_cash(self) -> int:
        return self.cash + sum(subsidiary.total_cash() for subsidiary in self.subsidiaries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "name": self.name,
            "cash": self.cash,
            "reputation": self.reputation,
            "executives": [executive.to_dict() for executive in self.executives],
            "divisions": [division.to_dict() for division in self.divisions],
            "assets": [asset.to_dict() for asset in self.assets],
            "stock_profile": self.stock_profile.to_dict(),
            "loans": [loan.to_dict() for loan in self.loans],
            "npc_traits": [trait.value for trait in self.npc_traits],
            "subsidiaries": [subsidiary.to_dict() for subsidiary in self.subsidiaries],
            "industry_id": self.industry_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Company:
        return cls(
            company_id=str(data["company_id"]),
            name=str(data["name"]),
            cash=int(data.get("cash", 0)),
            reputation=float(data.get("reputation", 50.0)),
            executives=[Executive.from_dict(executive) for executive in data.get("executives", [])],
            divisions=[Division.from_dict(division) for division in data.get("divisions", [])],
            assets=[Asset.from_dict(asset) for asset in data.get("assets", [])],
            stock_profile=StockProfile.from_dict(data.get("stock_profile")),
            loans=[Loan.from_dict(loan) for loan in data.get("loans", [])],
            npc_traits=tuple(
                NPCCompanyTrait(str(trait)) for trait in data.get("npc_traits", ())
            ),
            subsidiaries=[Company.from_dict(company) for company in data.get("subsidiaries", [])],
            industry_id=data.get("industry_id"),
        )


@dataclass(slots=True)
class HoldingCompany:
    name: str
    holding_company_id: str = field(default_factory=lambda: _new_id("holding"))
    cash: int = 0
    reputation: float = 50.0
    executives: list[Executive] = field(default_factory=list)
    companies: list[Company] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_cash(self.cash)
        _validate_reputation(self.reputation)

    @property
    def division_count(self) -> int:
        return sum(len(company.divisions) for company in self.companies)

    @property
    def branch_count(self) -> int:
        return sum(company.branch_count for company in self.companies)

    @property
    def department_count(self) -> int:
        return sum(company.department_count for company in self.companies)

    @property
    def manager_count(self) -> int:
        return sum(company.manager_count for company in self.companies)

    def add_cash(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cash additions cannot be negative.")

        self.cash += amount

    def spend_cash(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cash spending cannot be negative.")
        if amount > self.cash:
            raise ValueError("Holding company does not have enough cash.")

        self.cash -= amount

    def add_company(self, company: Company) -> None:
        if self.get_company(company.company_id) is not None:
            raise ValueError(f"Company already exists: {company.company_id}")

        self.companies.append(company)

    def add_executive(self, executive: Executive) -> None:
        self.executives.append(executive)

    def get_company(self, company_id: str) -> Company | None:
        for company in self.companies:
            if company.company_id == company_id:
                return company

            subsidiary = company.get_subsidiary(company_id)
            if subsidiary is not None:
                return subsidiary

        return None

    def total_cash(self) -> int:
        return self.cash + sum(company.total_cash() for company in self.companies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "holding_company_id": self.holding_company_id,
            "name": self.name,
            "cash": self.cash,
            "reputation": self.reputation,
            "executives": [executive.to_dict() for executive in self.executives],
            "companies": [company.to_dict() for company in self.companies],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HoldingCompany:
        return cls(
            holding_company_id=str(data["holding_company_id"]),
            name=str(data["name"]),
            cash=int(data.get("cash", 0)),
            reputation=float(data.get("reputation", 50.0)),
            executives=[Executive.from_dict(executive) for executive in data.get("executives", [])],
            companies=[Company.from_dict(company) for company in data.get("companies", [])],
        )


@dataclass(slots=True)
class Player:
    name: str
    holding_company: HoldingCompany
    player_id: str = field(default_factory=lambda: _new_id("player"))

    @classmethod
    def starter(cls) -> Player:
        return cls(
            name="Player",
            holding_company=HoldingCompany(
                name="Platinum Holdings",
                cash=5000000,
                reputation=50.0,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "holding_company": self.holding_company.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Player:
        return cls(
            player_id=str(data["player_id"]),
            name=str(data["name"]),
            holding_company=HoldingCompany.from_dict(data["holding_company"]),
        )
