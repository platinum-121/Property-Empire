# gameplay/service.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from random import Random
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from companies.models import Asset, Branch, BranchType, Company, Division, Executive, HoldingCompany, SkillRatings
from finance.models import BalanceSheet, CreditRating, Loan
from gameplay.models import CityManagerProfile, MegaProjectOpportunity, ResearchEffect
from industries.real_estate.economy import (
    ConstructionCompany,
    DealRarity,
    DevelopmentOption,
    DevelopmentProject,
    EconomyConfig,
    LandListing,
    LandMarketplace,
    LandParcel,
    LoanApproval,
    PropertyListing,
    PropertyMarketplace,
    PurchaseQuote,
    Zoning,
    default_construction_companies,
    default_development_options,
    load_economy_config,
)
from industries.real_estate.industry import RealEstateIndustry
from industries.real_estate.models import BuildingType, Property, Tenant
from news.models import NewsCategory
from world.models import City, Country

if TYPE_CHECKING:
    from core.state import GameState


@dataclass(frozen=True, slots=True)
class OperatingResult:
    revenue: int = 0
    expenses: int = 0

    @property
    def profit(self) -> int:
        return self.revenue - self.expenses


@dataclass(frozen=True, slots=True)
class ResearchNode:
    node_id: str
    category: str
    name: str
    description: str
    cost: int
    prerequisites: tuple[str, ...] = ()
    effects: tuple[ResearchEffect, ...] = ()


@dataclass(frozen=True, slots=True)
class NegotiationResult:
    negotiation_id: str
    target_id: str
    target_type: str
    player_offer: int
    seller_response: str
    status: str
    counteroffer: int | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class PortfolioAcquisitionOpportunity:
    company_id: str
    company_name: str
    portfolio_value: int
    debt: int
    cities: tuple[str, ...]
    property_count: int
    revenue_month: int
    profit_month: int
    asking_price: int


class GameplayService:
    COMPANY_START_CASH = 250000
    EXECUTIVE_SIGNING_COST = 125000
    DEFAULT_LOAN_PRINCIPAL = 500000
    RESEARCH_NODES: tuple[ResearchNode, ...] = (
        ResearchNode("tenant_screening", "Property Management", "Tenant Screening", "Raise expected occupancy and reduce vacancy shocks.", 125000, effects=(ResearchEffect("occupancy", 0.04, "+4.0% occupancy"), ResearchEffect("vacancy_risk", -0.03, "-3.0% vacancy shock risk"))),
        ResearchNode("preventive_maintenance", "Property Management", "Preventive Maintenance", "Lower maintenance leakage across the portfolio.", 160000, effects=(ResearchEffect("maintenance", 0.06, "-6.0% maintenance cost"),)),
        ResearchNode("rent_analytics", "Property Management", "Rent Analytics", "Improve pricing discipline on rented space.", 450000, ("tenant_screening",), (ResearchEffect("rent", 0.03, "+3.0% rent income"),)),
        ResearchNode("centralised_leasing", "Property Management", "Centralised Leasing", "Fill vacant units faster across operating cities.", 1_250_000, ("tenant_screening",), (ResearchEffect("occupancy", 0.03, "+3.0% occupancy"),)),
        ResearchNode("predictive_maintenance", "Property Management", "Predictive Maintenance", "Use condition data to prevent expensive repairs.", 2_500_000, ("preventive_maintenance",), (ResearchEffect("maintenance", 0.05, "-5.0% maintenance cost"), ResearchEffect("vacancy_risk", -0.02, "-2.0% vacancy shock risk"))),
        ResearchNode("dynamic_pricing", "Property Management", "Dynamic Pricing Engine", "Adjust rents city-by-city as demand moves.", 12_500_000, ("rent_analytics", "centralised_leasing"), (ResearchEffect("rent", 0.05, "+5.0% rent income"),)),
        ResearchNode("property_management_division", "Property Management", "Property Management Division", "Unlock city managers for routine small property purchases.", 150_000_000, ("centralised_leasing", "predictive_maintenance"), (ResearchEffect("city_manager_unlock", 1.0, "Unlocks City Managers"), ResearchEffect("manager_effectiveness", 0.10, "+10.0% city manager monthly budget efficiency"))),
        ResearchNode("autonomous_asset_management", "Property Management", "Autonomous Asset Management", "Automate portfolio tuning at institutional scale.", 1_500_000_000, ("dynamic_pricing", "property_management_division"), (ResearchEffect("rent", 0.08, "+8.0% rent income"), ResearchEffect("occupancy", 0.04, "+4.0% occupancy"), ResearchEffect("manager_effectiveness", 0.15, "+15.0% city manager monthly budget efficiency"))),
        ResearchNode("site_logistics", "Development", "Site Logistics", "Reduce idle time and site sequencing losses.", 180000, effects=(ResearchEffect("construction_time", 0.05, "-5.0% construction time"),)),
        ResearchNode("bulk_procurement", "Development", "Bulk Procurement", "Buy materials at portfolio scale.", 220000, ("site_logistics",), (ResearchEffect("construction_cost", 0.04, "-4.0% construction cost"),)),
        ResearchNode("modular_design", "Development", "Modular Design", "Standardise repeatable building components.", 800000, ("site_logistics",), (ResearchEffect("construction_time", 0.04, "-4.0% construction time"),)),
        ResearchNode("prefab_supply_chain", "Development", "Prefab Supply Chain", "Reduce construction cost on repeatable projects.", 4_500_000, ("bulk_procurement", "modular_design"), (ResearchEffect("construction_cost", 0.06, "-6.0% construction cost"),)),
        ResearchNode("vertical_construction", "Development", "Vertical Construction Systems", "Improve tower delivery and lower high-rise execution risk.", 75_000_000, ("prefab_supply_chain",), (ResearchEffect("construction_time", 0.03, "-3.0% construction time"), ResearchEffect("mega_risk", -0.04, "-4.0% mega project risk"))),
        ResearchNode("mega_project_delivery", "Development", "Mega Project Delivery Office", "Create dedicated controls for the largest projects.", 2_000_000_000, ("vertical_construction",), (ResearchEffect("construction_cost", 0.08, "-8.0% construction cost"), ResearchEffect("construction_time", 0.08, "-8.0% construction time"), ResearchEffect("mega_risk", -0.08, "-8.0% mega project risk"))),
        ResearchNode("lender_relations", "Finance", "Lender Relations", "Build lender trust and reduce borrowing spreads.", 175000, effects=(ResearchEffect("loan_terms", 0.01, "-1.0% loan interest rate"),)),
        ResearchNode("credit_packaging", "Finance", "Credit Packaging", "Present lender packs with better data quality.", 210000, ("lender_relations",), (ResearchEffect("credit", 30, "+30 credit rating"),)),
        ResearchNode("debt_syndication", "Finance", "Debt Syndication", "Support larger secured loans across multiple lenders.", 3_000_000, ("lender_relations",), (ResearchEffect("loan_terms", 0.008, "-0.8% loan interest rate"), ResearchEffect("borrowing_capacity", 0.10, "+10.0% borrowing capacity"))),
        ResearchNode("institutional_capital", "Finance", "Institutional Capital Desk", "Make the company legible to institutional lenders.", 35_000_000, ("credit_packaging", "debt_syndication"), (ResearchEffect("credit", 35, "+35 credit rating"), ResearchEffect("borrowing_capacity", 0.15, "+15.0% borrowing capacity"))),
        ResearchNode("bond_programme", "Finance", "Bond Programme", "Lower cost of capital for large portfolios.", 250_000_000, ("institutional_capital",), (ResearchEffect("loan_terms", 0.012, "-1.2% loan interest rate"), ResearchEffect("borrowing_capacity", 0.20, "+20.0% borrowing capacity"))),
        ResearchNode("sovereign_scale_financing", "Finance", "Sovereign-Scale Financing", "Unlock top-tier capital access for national portfolios.", 3_500_000_000, ("bond_programme",), (ResearchEffect("loan_terms", 0.015, "-1.5% loan interest rate"), ResearchEffect("credit", 40, "+40 credit rating"), ResearchEffect("borrowing_capacity", 0.25, "+25.0% borrowing capacity"))),
        ResearchNode("zoning_liaison", "Planning", "Zoning Liaison", "Improve approval odds on planning cases.", 150000, effects=(ResearchEffect("planning_score", 15, "+15 planning score"),)),
        ResearchNode("large_project_permits", "Planning", "Large Project Permits", "Handle larger projects with fewer approval penalties.", 260000, ("zoning_liaison",), (ResearchEffect("planning_score", 10, "+10 planning score"), ResearchEffect("planning_threshold", 0.15, "+15.0% planning size threshold"))),
        ResearchNode("municipal_partnerships", "Planning", "Municipal Partnerships", "Earn city support for complex developments.", 1_500_000, ("zoning_liaison",), (ResearchEffect("planning_score", 10, "+10 planning score"), ResearchEffect("mega_risk", -0.03, "-3.0% mega project risk"))),
        ResearchNode("transit_oriented_development", "Planning", "Transit-Oriented Development", "Improve approvals and demand for dense city projects.", 18_000_000, ("large_project_permits", "municipal_partnerships"), (ResearchEffect("planning_score", 12, "+12 planning score"), ResearchEffect("occupancy", 0.02, "+2.0% occupancy"))),
        ResearchNode("urban_regeneration_authority", "Planning", "Urban Regeneration Authority", "Win public-sector confidence on major regeneration schemes.", 850_000_000, ("transit_oriented_development",), (ResearchEffect("planning_score", 25, "+25 planning score"), ResearchEffect("mega_risk", -0.05, "-5.0% mega project risk"))),
        ResearchNode("portfolio_controls", "Corporate", "Portfolio Controls", "Standardise operating controls across cities.", 190000, effects=(ResearchEffect("operating_margin", 0.02, "+2.0% operating margin"),)),
        ResearchNode("regional_reporting", "Corporate", "Regional Reporting", "Improve regional visibility and manager oversight.", 140000, effects=(ResearchEffect("operating_margin", 0.01, "+1.0% operating margin"), ResearchEffect("manager_effectiveness", 0.05, "+5.0% city manager monthly budget efficiency"))),
        ResearchNode("portfolio_risk_office", "Corporate", "Portfolio Risk Office", "Reduce avoidable downside and vacancy exposure.", 950000, ("portfolio_controls", "regional_reporting"), (ResearchEffect("operating_margin", 0.015, "+1.5% operating margin"), ResearchEffect("vacancy_risk", -0.03, "-3.0% vacancy shock risk"))),
        ResearchNode("acquisition_integration", "Corporate", "Acquisition Integration", "Improve acquired portfolio handover economics.", 7_500_000, ("portfolio_risk_office",), (ResearchEffect("acquisition_discount", 0.04, "-4.0% portfolio acquisition price"), ResearchEffect("operating_margin", 0.01, "+1.0% operating margin"))),
        ResearchNode("global_operating_model", "Corporate", "Global Operating Model", "Scale the operating model without losing control.", 120_000_000, ("acquisition_integration",), (ResearchEffect("operating_margin", 0.025, "+2.5% operating margin"), ResearchEffect("manager_effectiveness", 0.10, "+10.0% city manager monthly budget efficiency"))),
        ResearchNode("property_empire_platform", "Corporate", "Property Empire Platform", "End-game platform for a national property empire.", 5_000_000_000, ("global_operating_model", "autonomous_asset_management", "mega_project_delivery", "sovereign_scale_financing", "urban_regeneration_authority"), (ResearchEffect("operating_margin", 0.04, "+4.0% operating margin"), ResearchEffect("rent", 0.03, "+3.0% rent income"), ResearchEffect("mega_risk", -0.06, "-6.0% mega project risk"))),
    )

    def __init__(self) -> None:
        self._config: EconomyConfig = load_economy_config()
        self._real_estate = RealEstateIndustry()
        self._property_marketplace = PropertyMarketplace(self._config)
        self._land_marketplace = LandMarketplace(self._config)
        self._construction_companies = default_construction_companies()
        self._development_options = default_development_options()

    def new_game(
        self,
        company_name: str,
        starting_industry: str = "real_estate",
        hq_city_id: str = "new_york_city",
    ) -> GameState:
        from core.state import GameState

        clean_name = " ".join(company_name.strip().split())
        if not clean_name:
            raise ValueError("Company name is required.")
        if starting_industry != "real_estate":
            raise ValueError("Property Empire Simulator supports Real Estate only.")

        state = GameState(world_name=f"{clean_name} World")
        city = state.world.get_city(hq_city_id)
        if city is None:
            raise ValueError(f"Unknown HQ city: {hq_city_id}")

        state.player.holding_company.name = f"{clean_name} Holdings"
        company = Company(
            name=clean_name,
            company_id=self._company_id(clean_name),
            cash=self.COMPANY_START_CASH,
            reputation=55.0,
            industry_id="real_estate",
        )
        division = Division(name="Property Operations", division_id=f"{company.company_id}_properties")
        division.add_branch(
            Branch(
                name=f"{city.name} HQ",
                branch_id=f"{company.company_id}_hq",
                city_id=city.city_id,
                branch_type=BranchType.HQ,
            )
        )
        company.add_division(division)
        company.add_executive(
            Executive(
                name=f"{clean_name} CEO",
                title="CEO",
                salary=180000,
                loyalty=72.0,
                reputation=65.0,
                traits=("founder",),
                workload_percent=85.0,
                skills=SkillRatings(
                    leadership=72.0,
                    finance=66.0,
                    operations=68.0,
                    negotiation=64.0,
                    people=68.0,
                ),
            )
        )
        self._spend_group_cash(state, self.COMPANY_START_CASH)
        state.player.holding_company.add_company(company)
        state.metadata.update(
            {
                "economy_date": state.clock.current_date.isoformat(),
                "game_started": True,
                "quarter_taxable_profit": 0,
                "quarter_start_debt": 0,
                "quarter_start_portfolio_value": 0,
                "quarter_start_occupancy": 0.0,
                "quarter_start_credit_rating": self.credit_rating(state).score,
                "starting_industry": "real_estate",
                "hq_city_id": city.city_id,
                "hq_city_name": city.name,
                "company_name": clean_name,
                "last_month_revenue": 0,
                "last_month_expenses": 0,
                "last_month_profit": 0,
            }
        )
        state.news_feed.add(
            f"{clean_name} Opens Headquarters In {city.name}",
            NewsCategory.COMPANY,
            state.clock.current_date,
        )
        return state

    def ensure_starting_company(self, state: GameState) -> Company:
        holding = state.player.holding_company
        existing = holding.get_company("platinum_properties")
        if existing is not None:
            return existing
        if holding.companies:
            return holding.companies[0]

        if holding.cash < self.COMPANY_START_CASH:
            raise ValueError("Not enough cash to start a property company.")

        holding.spend_cash(self.COMPANY_START_CASH)
        company = Company(
            name="Platinum Properties",
            company_id="platinum_properties",
            cash=self.COMPANY_START_CASH,
            reputation=55.0,
            industry_id="real_estate",
        )
        company.add_division(Division(name="Property Operations", division_id="platinum_properties_ops"))
        holding.add_company(company)
        state.metadata.setdefault("economy_date", state.clock.current_date.isoformat())
        state.metadata.setdefault("quarter_taxable_profit", 0)
        state.metadata.setdefault("quarter_start_debt", self._total_debt(state))
        state.metadata.setdefault("quarter_start_portfolio_value", self._portfolio_value(state))
        state.metadata.setdefault("quarter_start_occupancy", self._portfolio_occupancy(state))
        state.metadata.setdefault("quarter_start_credit_rating", self.credit_rating(state).score)
        state.metadata.setdefault("starting_industry", "real_estate")
        state.metadata.setdefault("last_month_revenue", 0)
        state.metadata.setdefault("last_month_expenses", 0)
        state.metadata.setdefault("last_month_profit", 0)
        state.news_feed.add(
            "Platinum Holdings Launches Platinum Properties",
            NewsCategory.COMPANY,
            state.clock.current_date,
        )
        return company

    def property_listings(self, state: GameState, city_id: str) -> tuple[PropertyListing, ...]:
        city = state.world.get_city(city_id)
        if city is None:
            raise ValueError(f"Unknown city: {city_id}")
        return self._property_marketplace.active_listings(city)

    def all_property_listings(self, state: GameState) -> list[PropertyListing]:
        listings: list[PropertyListing] = []
        for city in state.world.cities:
            listings.extend(self.property_listings(state, city.city_id))
        return listings

    def filter_property_deals(
        self,
        state: GameState,
        search: str = "",
        city_id: str = "",
        country_id: str = "",
        zoning: str = "",
        min_price: int | None = None,
        max_price: int | None = None,
        min_yield: float | None = None,
        max_size_sqm: int | None = None,
        rarity: str = "",
        sort_key: str = "yield_high",
    ) -> list[PropertyListing]:
        listings = list(self.property_listings(state, city_id)) if city_id else self.all_property_listings(state)
        query = search.strip().lower()
        filtered = []
        for listing in listings:
            context = state.world.city_context(listing.city_id)
            if context is None:
                continue
            _, country, _, city = context
            if country_id and country.country_id != country_id:
                continue
            if zoning and listing.zoning.value != zoning:
                continue
            if rarity and listing.rarity.value != rarity:
                continue
            if min_price is not None and listing.asking_price < min_price:
                continue
            if max_price is not None and listing.asking_price > max_price:
                continue
            if min_yield is not None and listing.annual_yield < min_yield:
                continue
            if max_size_sqm is not None and listing.size_sqm > max_size_sqm:
                continue
            haystack = f"{listing.name} {listing.property_type} {listing.zoning.value} {city.name} {country.name}".lower()
            if query and query not in haystack:
                continue
            filtered.append(listing)

        reverse = sort_key.endswith("_high") or sort_key in {"days_remaining"}
        key_name = sort_key.replace("_low", "").replace("_high", "")
        filtered.sort(key=lambda listing: self._deal_sort_value(listing, key_name), reverse=reverse)
        return filtered

    def land_listings(self, state: GameState, city_id: str) -> tuple[LandListing, ...]:
        city = state.world.get_city(city_id)
        if city is None:
            raise ValueError(f"Unknown city: {city_id}")
        return self._land_marketplace.active_listings(city)

    def all_land_listings(self, state: GameState) -> list[LandListing]:
        listings: list[LandListing] = []
        for city in state.world.cities:
            listings.extend(self.land_listings(state, city.city_id))
        return listings

    def construction_companies(self) -> tuple[ConstructionCompany, ...]:
        return self._construction_companies

    def development_options(self, zoning: Zoning | str | None = None) -> tuple[DevelopmentOption, ...]:
        if zoning is None or zoning == "":
            return self._development_options
        zoning_value = zoning if isinstance(zoning, Zoning) else Zoning(str(zoning))
        return tuple(option for option in self._development_options if option.zoning is zoning_value)

    def development_quote(
        self,
        state: GameState,
        parcel_id: str,
        option_id: str,
        construction_company_id: str,
    ) -> dict[str, int | float | str | bool]:
        parcel = self._find_owned_land(state, parcel_id)
        option = self._development_option(option_id)
        if option.zoning is not parcel.zoning:
            raise ValueError(f"{option.name} requires {option.zoning.value} zoning.")
        company = self._construction_company(construction_company_id)
        city = self._require_city(state, parcel.city_id)
        size = parcel.size_sqm
        bonuses = self._research_bonuses(state)
        cost = round(size * option.construction_cost_per_sqm * city.property_multiplier * company.cost_multiplier * (1 - bonuses["construction_cost"]))
        build_days = max(30, round((option.base_build_days * (1 - bonuses["construction_time"])) / company.speed_multiplier))
        rent = round(size * option.rent_per_sqm * parcel.demand_multiplier * city.property_multiplier)
        maintenance = round(rent * option.maintenance_ratio)
        profit = rent - maintenance
        unit_count = max(1, round((size / 1000) * option.unit_density_per_1000_sqm))
        planning = self.planning_assessment(state, parcel.parcel_id, option.option_id)
        return {
            "name": option.name,
            "zoning": option.zoning.value,
            "construction_company": company.name,
            "construction_cost": cost,
            "build_time_days": build_days,
            "unit_count": unit_count,
            "expected_rent": rent,
            "expected_maintenance": maintenance,
            "expected_profit": profit,
            "expected_yield": (profit * 12 / cost) if cost else 0.0,
            "planning_required": planning["required"],
            "planning_approved": planning["approved"],
            "planning_score": planning["score"],
            "planning_reason": planning["reason"],
            "overrun_chance": company.overrun_chance,
            "delay_chance": company.delay_chance,
        }

    def planning_assessment(self, state: GameState, parcel_id: str, option_id: str) -> dict[str, int | float | str | bool]:
        parcel = self._find_owned_land(state, parcel_id)
        option = self._development_option(option_id)
        city = self._require_city(state, parcel.city_id)
        bonuses = self._research_bonuses(state)
        threshold = round(self._config.planning_size_thresholds.get(parcel.zoning, 20000) * (1 + bonuses["planning_threshold"]))
        required = option.planning_required or parcel.size_sqm > threshold
        if not required:
            return {"required": False, "approved": True, "score": 100, "reason": "No planning approval required."}

        reputation = self._average_company_reputation(state)
        size_penalty = (parcel.size_sqm / 10000) * self._config.planning_size_penalty_per_10000_sqm
        research_bonus = bonuses["planning_score"]
        large_project_bonus = 10 if "large_project_permits" in self._completed_research(state) else 0
        score = round(
            self._config.planning_base_approval_score
            + (city.demand_score * self._config.planning_demand_weight)
            + (reputation * self._config.planning_reputation_weight)
            + research_bonus
            + large_project_bonus
            - size_penalty
        )
        approved = score >= 70
        reason = "Planning likely approved." if approved else "Planning risk too high for this project size and market."
        return {"required": True, "approved": approved, "score": max(0, min(100, score)), "reason": reason}

    def quote_property_purchase(
        self,
        state: GameState,
        listing_id: str,
        deposit_percent: float = 1.0,
        term_months: int = 120,
        negotiated_price: int | None = None,
    ) -> PurchaseQuote:
        self._require_property_game(state)
        listing = self._find_property_listing(state, listing_id)
        if not 0 <= deposit_percent <= 1:
            raise ValueError("Deposit percent must be between 0 and 1.")

        purchase_price = negotiated_price if negotiated_price is not None else listing.asking_price
        if purchase_price <= 0:
            raise ValueError("Purchase price must be greater than zero.")

        taxes_and_fees = round(purchase_price * self._config.stamp_duty_rate)
        deposit = round(purchase_price * deposit_percent)
        loan_amount = purchase_price - deposit
        cash_required = deposit + taxes_and_fees
        approval = self._loan_approval(
            state=state,
            requested_loan_amount=loan_amount,
            term_months=term_months,
            projected_monthly_profit=listing.monthly_profit,
            collateral_value=purchase_price,
        )
        reasons = list(approval.reasons)
        if loan_amount and deposit_percent < self._config.minimum_deposit_percent:
            reasons.append("Insufficient deposit.")
            approval = LoanApproval(
                False,
                "Insufficient deposit.",
                approval.max_loan_amount,
                loan_amount,
                approval.interest_rate,
                term_months,
                approval.monthly_repayment,
                tuple(reasons),
            )

        loan = None
        if loan_amount:
            loan = Loan.quote(
                principal=loan_amount,
                term_months=term_months,
                credit_rating=self.credit_rating(state),
                balance_sheet=self._group_balance_sheet(state, extra_asset_value=purchase_price),
                base_rate=max(0.005, self._config.base_interest_rate - self._research_bonuses(state)["loan_terms"]),
            )
        return PurchaseQuote(
            listing_id=listing.listing_id,
            purchase_price=purchase_price,
            deposit_percent=deposit_percent,
            deposit_amount=deposit,
            loan_amount=loan_amount,
            taxes_and_fees=taxes_and_fees,
            cash_required=cash_required,
            approval=approval,
            loan=loan,
        )

    def buy_property_listing(
        self,
        state: GameState,
        listing_id: str,
        deposit_percent: float = 1.0,
        term_months: int = 120,
        negotiated_price: int | None = None,
    ) -> Property:
        company = self.ensure_starting_company(state)
        listing = self._find_property_listing(state, listing_id)
        quote = self.quote_property_purchase(state, listing_id, deposit_percent, term_months, negotiated_price)
        if quote.cash_required > state.player.holding_company.total_cash():
            raise ValueError("Not enough cash for purchase deposit, taxes, and fees.")
        if quote.loan_amount and not quote.approval.approved:
            raise ValueError(f"Bank declined financing: {quote.approval.reason}")

        if quote.loan_amount:
            loan = company.take_loan(
                principal=quote.loan_amount,
                term_months=term_months,
                credit_rating=self.credit_rating(state),
                base_rate=max(0.005, self._config.base_interest_rate - self._research_bonuses(state)["loan_terms"]),
            )
            loan.name = f"Acquisition Loan - {listing.name}"
            loan.secured_asset_id = listing.listing_id
            state.financials.cash_flow.add_financing("property_loan_draw", quote.loan_amount)

        self._spend_group_cash(state, quote.purchase_price + quote.taxes_and_fees)
        property_ = self._property_from_listing(listing, quote.purchase_price)
        state.player_properties.append(property_)
        state.financials.cash_flow.add_investing("property_purchase", -quote.purchase_price)
        state.financials.cash_flow.add_operating("stamp_duty_paid", -quote.taxes_and_fees)
        state.financials.income_statement.add_expense("stamp_duty_paid", quote.taxes_and_fees)
        state.news_feed.add(
            f"{property_.name} Purchased In {self._city_name(state, listing.city_id)}",
            NewsCategory.REAL_ESTATE,
            self._economy_date(state),
        )
        return property_

    def buy_property(
        self,
        state: GameState,
        city_id: str = "new_york_city",
        building_type_id: str = "small_office",
    ) -> Property:
        _ = building_type_id
        listing = min(self.property_listings(state, city_id), key=lambda item: item.asking_price)
        return self.buy_property_listing(state, listing.listing_id, deposit_percent=1.0)

    def estimate_property_purchase(
        self,
        state: GameState,
        city_id: str,
        building_type_id: str,
    ) -> dict[str, int | float | str]:
        listing = self.property_listings(state, city_id)[0]
        return self.deal_detail(state, listing.listing_id)

    def deal_detail(self, state: GameState, listing_id: str) -> dict[str, int | float | str]:
        listing = self._find_property_listing(state, listing_id)
        context = state.world.city_context(listing.city_id)
        country_name = context[1].name if context is not None else ""
        city_name = context[3].name if context is not None else listing.city_id
        return {
            "listing_id": listing.listing_id,
            "building_name": listing.name,
            "property_type": listing.property_type,
            "city": city_name,
            "country": country_name,
            "size_sqm": listing.size_sqm,
            "zoning": listing.zoning.value,
            "cost": listing.asking_price,
            "asking_price": listing.asking_price,
            "rent": listing.monthly_revenue,
            "rent_low": listing.estimated_rent_low,
            "rent_high": listing.estimated_rent_high,
            "rent_per_sqm": listing.rent_per_sqm,
            "demand_multiplier": listing.demand_multiplier,
            "maintenance": listing.monthly_expenses,
            "profit": listing.monthly_profit,
            "yield": listing.annual_yield,
            "occupancy": listing.occupancy_rate,
            "rarity": listing.rarity.value,
            "days_remaining": listing.days_remaining,
            "available_cash": state.player.holding_company.total_cash(),
        }

    def negotiate_property_offer(self, state: GameState, listing_id: str, offer_amount: int) -> NegotiationResult:
        listing = self._find_property_listing(state, listing_id)
        return self._negotiate(
            state=state,
            target_id=listing.listing_id,
            target_type="property",
            asking_price=listing.asking_price,
            offer_amount=offer_amount,
            days_remaining=listing.days_remaining,
        )

    def negotiate_land_offer(self, state: GameState, listing_id: str, offer_amount: int) -> NegotiationResult:
        listing = self._find_land_listing(state, listing_id)
        return self._negotiate(
            state=state,
            target_id=listing.listing_id,
            target_type="land",
            asking_price=listing.asking_price,
            offer_amount=offer_amount,
            days_remaining=listing.days_remaining,
        )

    def withdraw_negotiation(self, state: GameState, negotiation_id: str) -> None:
        negotiations = dict(state.metadata.get("negotiations", {}))
        if negotiation_id not in negotiations:
            raise ValueError("Negotiation not found.")
        negotiations[negotiation_id]["status"] = "Withdrawn"
        negotiations[negotiation_id]["seller_response"] = "Withdrawn"
        state.metadata["negotiations"] = negotiations

    def accept_counteroffer(self, state: GameState, negotiation_id: str) -> NegotiationResult:
        negotiations = dict(state.metadata.get("negotiations", {}))
        negotiation = negotiations.get(negotiation_id)
        if negotiation is None:
            raise ValueError("Negotiation not found.")
        counteroffer = negotiation.get("counteroffer")
        if not counteroffer:
            raise ValueError("No counteroffer is available to accept.")

        accepted = NegotiationResult(
            negotiation_id=negotiation_id,
            target_id=str(negotiation["target_id"]),
            target_type=str(negotiation["target_type"]),
            player_offer=int(counteroffer),
            seller_response="Accept",
            status="Accepted",
            counteroffer=None,
            message=f"Seller accepted at {_format_money(int(counteroffer))}.",
        )
        negotiations[negotiation_id] = {
            "target_id": accepted.target_id,
            "target_type": accepted.target_type,
            "player_offer": accepted.player_offer,
            "seller_response": accepted.seller_response,
            "status": accepted.status,
            "counteroffer": accepted.counteroffer,
            "message": accepted.message,
        }
        state.metadata["negotiations"] = negotiations
        return accepted

    def buy_land_listing(
        self,
        state: GameState,
        listing_id: str,
        deposit_percent: float = 1.0,
        term_months: int = 120,
    ) -> LandParcel:
        listing = self._find_land_listing(state, listing_id)
        taxes_and_fees = round(listing.asking_price * self._config.stamp_duty_rate)
        deposit = round(listing.asking_price * deposit_percent)
        loan_amount = listing.asking_price - deposit
        approval = self._loan_approval(
            state=state,
            requested_loan_amount=loan_amount,
            term_months=term_months,
            projected_monthly_profit=0,
            collateral_value=listing.asking_price,
        )
        if deposit + taxes_and_fees > state.player.holding_company.total_cash():
            raise ValueError("Not enough cash for land deposit, taxes, and fees.")
        if loan_amount and not approval.approved:
            raise ValueError(f"Bank declined land financing: {approval.reason}")
        company = self.ensure_starting_company(state)
        if loan_amount:
            loan = company.take_loan(
                principal=loan_amount,
                term_months=term_months,
                credit_rating=self.credit_rating(state),
                base_rate=max(0.005, self._config.base_interest_rate - self._research_bonuses(state)["loan_terms"]),
            )
            loan.name = f"Land Loan - {listing.name}"
            loan.secured_asset_id = listing.listing_id
            state.financials.cash_flow.add_financing("land_loan_draw", loan_amount)
        self._spend_group_cash(state, listing.asking_price + taxes_and_fees)
        parcel = LandParcel(
            name=listing.name,
            city_id=listing.city_id,
            purchase_price=listing.asking_price,
            size_sqm=listing.size_sqm,
            zoning=listing.zoning,
            demand_multiplier=listing.demand_multiplier,
            parcel_id=listing.listing_id,
        )
        state.player_land.append(parcel)
        state.financials.cash_flow.add_investing("land_purchase", -listing.asking_price)
        state.financials.cash_flow.add_operating("stamp_duty_paid", -taxes_and_fees)
        state.financials.income_statement.add_expense("stamp_duty_paid", taxes_and_fees)
        state.news_feed.add(
            f"Development Site Purchased In {self._city_name(state, listing.city_id)}",
            NewsCategory.REAL_ESTATE,
            self._economy_date(state),
        )
        return parcel

    def start_development(
        self,
        state: GameState,
        parcel_id: str,
        option_id: str,
        construction_company_id: str = "metroconstruct",
    ) -> DevelopmentProject:
        parcel = self._find_owned_land(state, parcel_id)
        if parcel.developed:
            raise ValueError("Land parcel is already developed.")
        if any(project.parcel_id == parcel_id for project in state.development_projects):
            raise ValueError("Land parcel already has an active development.")
        quote = self.development_quote(state, parcel_id, option_id, construction_company_id)
        if bool(quote["planning_required"]) and not bool(quote["planning_approved"]):
            self._add_alert(state, "Planning rejected", str(quote["planning_reason"]), "Planning")
            state.news_feed.add("Planning Permission Rejected", NewsCategory.REAL_ESTATE, self._economy_date(state))
            raise ValueError(str(quote["planning_reason"]))
        if bool(quote["planning_required"]):
            self._add_alert(state, "Planning approved", f"{quote['name']} cleared planning.", "Planning")
            state.news_feed.add("Planning Permission Approved", NewsCategory.REAL_ESTATE, self._economy_date(state))
        cost = int(quote["construction_cost"])
        self._spend_group_cash(state, cost)
        state.metadata["month_construction_cost"] = int(state.metadata.get("month_construction_cost", 0)) + cost
        project = DevelopmentProject(
            parcel_id=parcel.parcel_id,
            city_id=parcel.city_id,
            option_id=option_id,
            building_name=f"{self._city_name(state, parcel.city_id)} {quote['name']}",
            zoning=parcel.zoning,
            construction_company_id=construction_company_id,
            total_cost=cost,
            total_days=int(quote["build_time_days"]),
            days_remaining=int(quote["build_time_days"]),
            size_sqm=parcel.size_sqm,
            expected_monthly_rent=int(quote["expected_rent"]),
            expected_monthly_maintenance=int(quote["expected_maintenance"]),
            unit_count=int(quote["unit_count"]),
        )
        state.development_projects.append(project)
        state.financials.cash_flow.add_investing("construction_start", -cost)
        state.news_feed.add(
            f"Construction Started On {project.building_name}",
            NewsCategory.REAL_ESTATE,
            self._economy_date(state),
        )
        return project

    def take_company_loan(
        self,
        state: GameState,
        principal: int = DEFAULT_LOAN_PRINCIPAL,
        term_months: int = 60,
    ) -> Loan:
        company = self.ensure_starting_company(state)
        approval = self._loan_approval(
            state=state,
            requested_loan_amount=principal,
            term_months=term_months,
            projected_monthly_profit=self._average_monthly_profit(state),
            collateral_value=0,
        )
        if not approval.approved:
            raise ValueError(f"Bank declined financing: {approval.reason}")
        loan = company.take_loan(
            principal=principal,
            term_months=term_months,
            credit_rating=self.credit_rating(state),
            base_rate=max(0.005, self._config.base_interest_rate - self._research_bonuses(state)["loan_terms"]),
        )
        loan.name = "Working Capital Property Loan"
        state.financials.cash_flow.add_financing("property_loan_draw", principal)
        state.news_feed.add(
            f"Property Loan Secured For {_format_money(principal)}",
            NewsCategory.FINANCE,
            self._economy_date(state),
        )
        return loan

    def estimate_company_loan(
        self,
        state: GameState,
        principal: int = DEFAULT_LOAN_PRINCIPAL,
        term_months: int = 60,
    ) -> dict[str, int | float | str | bool]:
        approval = self._loan_approval(
            state=state,
            requested_loan_amount=principal,
            term_months=term_months,
            projected_monthly_profit=self._average_monthly_profit(state),
            collateral_value=0,
        )
        return {
            "company": self.ensure_starting_company(state).name,
            "principal": principal,
            "term_months": term_months,
            "annual_interest_rate": approval.interest_rate,
            "monthly_repayment": approval.monthly_repayment,
            "total_interest_estimate": max(0, approval.monthly_repayment * term_months - principal),
            "approved": approval.approved,
            "reason": approval.reason,
            "max_loan_amount": approval.max_loan_amount,
        }

    def repay_company_loan(self, state: GameState, loan_id: str, amount: int) -> None:
        company = self._company_for_loan(state, loan_id)
        before = company.total_debt
        company.repay_loan(loan_id, amount)
        repayment = before - company.total_debt
        state.financials.cash_flow.add_financing("property_loan_repayment", -repayment)
        state.news_feed.add(
            f"Property Loan Repaid By {_format_money(repayment)}",
            NewsCategory.FINANCE,
            self._economy_date(state),
        )

    def loan_centre_rows(self, state: GameState) -> list[tuple[str, str, int, int, float, int, int, str, str]]:
        rows: list[tuple[str, str, int, int, float, int, int, str, str]] = []
        for company in self._all_companies(state.player.holding_company.companies):
            for loan in company.loans:
                rows.append(
                    (
                        loan.loan_id,
                        loan.name,
                        int(loan.original_principal or loan.principal),
                        loan.principal,
                        loan.annual_interest_rate,
                        int(loan.remaining_term_months or 0),
                        loan.monthly_payment,
                        loan.secured_asset_id or "Unsecured",
                        loan.status,
                    )
                )
        return rows

    def alerts(self, state: GameState, limit: int = 30) -> list[dict[str, Any]]:
        return list(state.metadata.get("alerts", []))[:limit]

    def pop_pending_reports(self, state: GameState) -> list[dict[str, Any]]:
        reports = list(state.metadata.get("pending_reports", []))
        state.metadata["pending_reports"] = []
        return reports

    def research_tree(self, state: GameState) -> list[dict[str, Any]]:
        completed = self._completed_research(state)
        active = str(state.metadata.get("active_research", ""))
        rows = []
        for node in self.RESEARCH_NODES:
            unlocked = all(prerequisite in completed for prerequisite in node.prerequisites)
            status = "Completed" if node.node_id in completed else "Active" if node.node_id == active else "Available" if unlocked else "Locked"
            rows.append(
                {
                    "node_id": node.node_id,
                    "category": node.category,
                    "name": node.name,
                    "description": node.description,
                    "effect_summary": "; ".join(effect.label for effect in node.effects),
                    "effects": tuple(effect.label for effect in node.effects),
                    "cost": node.cost,
                    "status": status,
                    "prerequisites": node.prerequisites,
                }
            )
        return rows

    def research_effect_rows(self, state: GameState) -> list[tuple[str, str, str, str]]:
        completed = self._completed_research(state)
        rows: list[tuple[str, str, str, str]] = []
        for node in self.RESEARCH_NODES:
            status = "Active" if node.node_id in completed else "Inactive"
            for effect in node.effects:
                rows.append((node.name, status, effect.label, node.description))
        return rows

    def start_research(self, state: GameState, node_id: str) -> None:
        node = next((item for item in self.RESEARCH_NODES if item.node_id == node_id), None)
        if node is None:
            raise ValueError(f"Unknown research: {node_id}")
        completed = self._completed_research(state)
        if node.node_id in completed:
            raise ValueError("Research already completed.")
        missing = [prerequisite for prerequisite in node.prerequisites if prerequisite not in completed]
        if missing:
            raise ValueError("Prerequisite research is missing.")
        self._spend_group_cash(state, node.cost)
        completed.add(node.node_id)
        state.metadata["completed_research"] = sorted(completed)
        state.metadata["active_research"] = ""
        self._add_alert(state, "Research complete", node.name, "Research")
        state.news_feed.add(f"Research Completed: {node.name}", NewsCategory.RESEARCH, self._economy_date(state))

    def city_manager_unlocked(self, state: GameState) -> bool:
        return "property_management_division" in self._completed_research(state)

    def city_manager_rows(self, state: GameState) -> list[dict[str, int | float | str]]:
        rows: list[dict[str, int | float | str]] = []
        for manager in self._city_managers(state).values():
            rows.append(
                {
                    "manager_id": manager.manager_id,
                    "name": manager.name,
                    "city": self._city_name(state, manager.city_id),
                    "city_id": manager.city_id,
                    "monthly_budget": manager.monthly_budget,
                    "min_yield": manager.min_yield,
                    "max_property_price": manager.max_property_price,
                    "allowed_property_types": ", ".join(manager.allowed_property_types),
                    "aggressiveness": manager.aggressiveness,
                    "cash_reserve_requirement": manager.cash_reserve_requirement,
                    "properties_purchased": manager.properties_purchased,
                    "capital_invested": manager.capital_invested,
                    "average_yield": manager.average_yield_achieved,
                    "status": manager.status,
                }
            )
        return sorted(rows, key=lambda row: str(row["city"]))

    def assign_city_manager(
        self,
        state: GameState,
        city_id: str,
        name: str,
        monthly_budget: int,
        min_yield: float,
        max_property_price: int,
        allowed_property_types: tuple[str, ...],
        aggressiveness: str = "Balanced",
        cash_reserve_requirement: int = 20_000_000,
    ) -> CityManagerProfile:
        if not self.city_manager_unlocked(state):
            raise ValueError("Research Property Management Division before assigning city managers.")
        self._require_city(state, city_id)
        if not any(property_.city_id == city_id for property_ in state.player_properties):
            raise ValueError("City managers can only be assigned where you operate.")
        managers = self._city_managers(state)
        if city_id in managers:
            raise ValueError("This city already has a manager.")
        if monthly_budget <= 0 or max_property_price <= 0:
            raise ValueError("Manager budget and maximum price must be greater than zero.")
        if not allowed_property_types:
            raise ValueError("Select at least one allowed property type.")
        clean_name = " ".join(name.strip().split()) or f"{self._city_name(state, city_id)} Manager"
        manager = CityManagerProfile(
            manager_id=f"city_manager_{uuid4().hex[:10]}",
            name=clean_name,
            city_id=city_id,
            monthly_budget=monthly_budget,
            min_yield=min_yield,
            max_property_price=max_property_price,
            allowed_property_types=tuple(allowed_property_types),
            aggressiveness=aggressiveness,
            cash_reserve_requirement=cash_reserve_requirement,
        )
        managers[city_id] = manager
        self._save_city_managers(state, managers)
        self._add_alert(state, "City manager assigned", f"{clean_name} assigned to {self._city_name(state, city_id)}.", "Management")
        return manager

    def update_city_manager(
        self,
        state: GameState,
        city_id: str,
        monthly_budget: int,
        min_yield: float,
        max_property_price: int,
        allowed_property_types: tuple[str, ...],
        aggressiveness: str,
        cash_reserve_requirement: int,
    ) -> CityManagerProfile:
        managers = self._city_managers(state)
        manager = managers.get(city_id)
        if manager is None:
            raise ValueError("City manager not found.")
        updated = CityManagerProfile(
            manager_id=manager.manager_id,
            name=manager.name,
            city_id=manager.city_id,
            monthly_budget=monthly_budget,
            min_yield=min_yield,
            max_property_price=max_property_price,
            allowed_property_types=tuple(allowed_property_types),
            aggressiveness=aggressiveness,
            cash_reserve_requirement=cash_reserve_requirement,
            properties_purchased=manager.properties_purchased,
            capital_invested=manager.capital_invested,
            yield_achieved_sum=manager.yield_achieved_sum,
            status="Active",
            month_spent=manager.month_spent,
            budget_month=manager.budget_month,
        )
        managers[city_id] = updated
        self._save_city_managers(state, managers)
        return updated

    def remove_city_manager(self, state: GameState, city_id: str) -> None:
        managers = self._city_managers(state)
        if city_id not in managers:
            raise ValueError("City manager not found.")
        removed = managers.pop(city_id)
        self._save_city_managers(state, managers)
        self._add_alert(state, "City manager removed", removed.name, "Management")

    def mega_project_eligible(self, state: GameState) -> bool:
        return self._portfolio_value(state) >= 1_000_000_000

    def mega_project_rows(self, state: GameState) -> list[dict[str, int | str]]:
        return [
            {
                **project.to_dict(),
                "location": self._city_name(state, project.city_id),
            }
            for project in self._mega_projects(state).values()
        ]

    def maybe_generate_mega_project(
        self,
        state: GameState,
        current_date: date | None = None,
        force: bool = False,
    ) -> MegaProjectOpportunity | None:
        current = current_date or self._economy_date(state)
        if not self.mega_project_eligible(state):
            return None
        projects = self._mega_projects(state)
        if any(project.status in {"Available", "Delayed", "Proceeding"} for project in projects.values()):
            return None
        last_year = int(state.metadata.get("last_mega_project_year", 0))
        if not force:
            if current.month != 1 or current.day != 1:
                return None
            if last_year and current.year - last_year < 2:
                return None
            random = Random(f"mega-project:{state.world_id}:{current.year}")
            if random.random() > 0.45:
                return None
        project = self._create_mega_project(state, current)
        projects[project.project_id] = project
        self._save_mega_projects(state, projects)
        state.metadata["last_mega_project_year"] = current.year
        self._add_alert(state, "Mega project available", f"{project.name} in {self._city_name(state, project.city_id)}.", "Mega Project")
        state.news_feed.add(f"Mega Project Available: {project.name}", NewsCategory.REAL_ESTATE, current)
        return project

    def proceed_mega_project(self, state: GameState, project_id: str) -> MegaProjectOpportunity:
        projects = self._mega_projects(state)
        project = projects.get(project_id)
        if project is None:
            raise ValueError("Mega project not found.")
        if project.status not in {"Available", "Delayed"}:
            raise ValueError("Mega project is not available.")
        reserve = round(project.estimated_cost * 0.2)
        self._spend_group_cash(state, reserve)
        updated = MegaProjectOpportunity(
            **{**project.to_dict(), "status": "Proceeding", "days_remaining": project.construction_days}
        )
        projects[project_id] = updated
        self._save_mega_projects(state, projects)
        state.financials.cash_flow.add_investing("mega_project_reserve", -reserve)
        self._add_alert(state, "Mega project proceeding", f"{project.name} capital reserved.", "Mega Project")
        return updated

    def delay_mega_project(self, state: GameState, project_id: str) -> None:
        projects = self._mega_projects(state)
        project = projects.get(project_id)
        if project is None:
            raise ValueError("Mega project not found.")
        projects[project_id] = MegaProjectOpportunity(
            **{**project.to_dict(), "status": "Delayed", "days_remaining": min(project.days_remaining, 365)}
        )
        self._save_mega_projects(state, projects)

    def reject_mega_project(self, state: GameState, project_id: str) -> None:
        projects = self._mega_projects(state)
        if project_id not in projects:
            raise ValueError("Mega project not found.")
        projects.pop(project_id)
        self._save_mega_projects(state, projects)

    def portfolio_acquisition_opportunities(self, state: GameState) -> list[PortfolioAcquisitionOpportunity]:
        opportunities = []
        top_cities = tuple(city.city_id for city in sorted(state.world.cities, key=lambda city: city.demand_score, reverse=True))
        for index, company in enumerate(state.npc_companies):
            portfolio_value = sum(asset.value for asset in company.assets)
            if portfolio_value <= 0:
                continue
            branch_cities = tuple(
                branch.city_id
                for division in company.divisions
                for branch in division.branches
                if branch.city_id
            )
            cities = branch_cities or top_cities[index % max(1, len(top_cities)) : index % max(1, len(top_cities)) + 1] or top_cities[:1]
            value_based_count = round(portfolio_value / 75_000_000)
            property_count = max(3, min(450, value_based_count + company.branch_count))
            revenue = round(portfolio_value * 0.0085)
            profit = round(revenue * (0.54 + min(company.reputation, 90) / 500))
            debt = company.total_debt
            asking_price = max(1, round(portfolio_value * 1.18 + company.cash * 0.12 - debt * 0.2))
            opportunities.append(
                PortfolioAcquisitionOpportunity(
                    company_id=company.company_id,
                    company_name=company.name,
                    portfolio_value=portfolio_value,
                    debt=debt,
                    cities=tuple(str(city_id) for city_id in cities),
                    property_count=property_count,
                    revenue_month=revenue,
                    profit_month=profit,
                    asking_price=asking_price,
                )
            )
        return sorted(opportunities, key=lambda item: item.asking_price)

    def buy_competitor_portfolio(self, state: GameState, company_id: str) -> None:
        opportunity = next((item for item in self.portfolio_acquisition_opportunities(state) if item.company_id == company_id), None)
        if opportunity is None:
            raise ValueError("No portfolio acquisition is available for that competitor.")
        company = next((item for item in state.npc_companies if item.company_id == company_id), None)
        if company is None:
            raise ValueError("Competitor not found.")
        discount = self._research_bonuses(state)["acquisition_discount"]
        final_price = round(opportunity.asking_price * max(0.75, 1 - discount))
        self._spend_group_cash(state, final_price)
        city_ids = opportunity.cities or (state.world.cities[0].city_id,)
        value_per_property = max(1, round(opportunity.portfolio_value / opportunity.property_count))
        revenue_per_property = max(1, round(opportunity.revenue_month / opportunity.property_count))
        profit_per_property = max(1, round(opportunity.profit_month / opportunity.property_count))
        for index in range(opportunity.property_count):
            city_id = city_ids[index % len(city_ids)]
            zoning = (Zoning.RESIDENTIAL, Zoning.OFFICE, Zoning.COMMERCIAL, Zoning.INDUSTRIAL)[index % 4]
            property_ = Property(
                name=f"{company.name} Portfolio Asset {index + 1}",
                building_type=self._building_type_for_zoning(zoning),
                city_id=city_id,
                property_id=f"{company.company_id}_acquired_{index + 1}",
                property_type="Acquired Portfolio Asset",
                zoning=zoning.value,
                size_sqm=1200 + (index * 160),
                purchase_price=value_per_property,
                expected_occupancy=0.84,
                monthly_revenue_override=revenue_per_property,
                monthly_expenses_override=max(0, revenue_per_property - profit_per_property),
                condition=0.84,
            )
            self._fill_tenants(property_, revenue_per_property, 0.84)
            state.player_properties.append(property_)
        company.assets.clear()
        state.financials.cash_flow.add_investing("portfolio_acquisition", -final_price)
        self._add_alert(state, "Portfolio acquired", opportunity.company_name, "Acquisition")
        state.news_feed.add(f"{opportunity.company_name} Portfolio Acquired", NewsCategory.REAL_ESTATE, self._economy_date(state))

    def portfolio_city_detail(self, state: GameState, city_name: str) -> dict[str, Any]:
        row = next((group for group in self.portfolio_by_city(state) if str(group["city"]) == city_name), None)
        if row is None:
            raise ValueError(f"No portfolio in {city_name}.")
        properties = [
            property_
            for property_ in state.player_properties
            if (city := state.world.get_city(property_.city_id)) is not None and city.name == city_name
        ]
        history = [
            item
            for item in state.metadata.get("operating_history", [])
            if city_name in item.get("city_profit", {})
        ]
        return {
            "summary": row,
            "property_count": len(properties),
            "history": history,
            "breakdown": [
                (
                    property_.name,
                    property_.zoning or property_.building_type.name,
                    property_.size_sqm,
                    property_.purchase_price,
                    property_.occupancy.rate,
                )
                for property_ in properties
            ],
        }

    def process_player_days(self, state: GameState, days: int) -> OperatingResult:
        if days <= 0:
            raise ValueError("Simulation days must be greater than zero.")

        self.ensure_starting_company(state)
        total = OperatingResult()
        for _ in range(days):
            current_date = self._advance_economy_date(state)
            self._process_development_day(state, current_date)
            self._process_mega_project_day(state, current_date)
            self.maybe_generate_mega_project(state, current_date=current_date)
            if current_date.day == 1:
                monthly = self._process_month(state, current_date)
                total = OperatingResult(
                    revenue=total.revenue + monthly.revenue,
                    expenses=total.expenses + monthly.expenses,
                )
                state.metadata["last_month_revenue"] = monthly.revenue
                state.metadata["last_month_expenses"] = monthly.expenses
                state.metadata["last_month_profit"] = monthly.profit
        state.metadata["last_revenue"] = total.revenue
        state.metadata["last_expenses"] = total.expenses
        state.metadata["last_profit"] = total.profit
        return total

    def credit_rating(self, state: GameState) -> CreditRating:
        score = sum(int(factor["impact"]) for factor in self.credit_rating_factors(state))
        score = max(0, min(800, score))
        return CreditRating(score=score)

    def credit_rating_factors(self, state: GameState) -> list[dict[str, int | str]]:
        cash = state.player.holding_company.total_cash()
        assets = max(self.company_value(state), 1)
        portfolio_value = self._portfolio_value(state)
        debt = self._total_debt(state)
        leverage = debt / assets
        average_profit = self._average_monthly_profit(state)
        delinquent_loans = sum(
            1
            for company in self._all_companies(state.player.holding_company.companies)
            for loan in company.loans
            if loan.status != "Current"
        )
        completed = self._completed_research(state)
        research_credit = int(self._research_bonuses(state)["credit"])
        factors = [
            {
                "factor": "Base company profile",
                "impact": 500,
                "status": "Active",
                "detail": "Starting lender confidence for an operating property company.",
            },
            {
                "factor": "Cash reserves",
                "impact": min(100, round(cash / 90000)),
                "status": "Active" if cash > 0 else "Inactive",
                "detail": f"{_format_money(cash)} available across the group.",
            },
            {
                "factor": "Monthly profit trend",
                "impact": max(-100, min(120, round(average_profit / 2200))),
                "status": "Active" if average_profit != 0 else "Inactive",
                "detail": f"Average monthly profit is {_format_money(average_profit)}.",
            },
            {
                "factor": "Property collateral",
                "impact": min(60, round(portfolio_value / 125000)),
                "status": "Active" if portfolio_value > 0 else "Inactive",
                "detail": f"Portfolio value is {_format_money(portfolio_value)}.",
            },
            {
                "factor": "Credit packaging research",
                "impact": research_credit,
                "status": "Active" if research_credit else "Inactive",
                "detail": "Finance research improves lender presentation quality.",
            },
            {
                "factor": "Low leverage bonus",
                "impact": 25 if debt == 0 and portfolio_value > 0 else 0,
                "status": "Active" if debt == 0 and portfolio_value > 0 else "Inactive",
                "detail": "Unlevered property assets improve borrowing confidence.",
            },
            {
                "factor": "Leverage penalty",
                "impact": -min(330, round(leverage * 460)),
                "status": "Active" if debt > 0 else "Inactive",
                "detail": f"Debt is {_format_money(debt)} against company value of {_format_money(assets)}.",
            },
            {
                "factor": "Delinquent loan penalty",
                "impact": -80 * delinquent_loans,
                "status": "Active" if delinquent_loans else "Inactive",
                "detail": f"{delinquent_loans} delinquent loan(s).",
            },
            {
                "factor": "Bankruptcy distress",
                "impact": -200 if bool(state.metadata.get("bankrupt", False)) else 0,
                "status": "Active" if bool(state.metadata.get("bankrupt", False)) else "Inactive",
                "detail": "Triggered when required obligations cannot be paid.",
            },
            {
                "factor": "Thin portfolio penalty",
                "impact": -35 if not state.player_properties else 0,
                "status": "Active" if not state.player_properties else "Inactive",
                "detail": "No owned operating properties yet.",
            },
        ]
        return factors

    def credit_profile(self, state: GameState) -> dict[str, Any]:
        rating = self.credit_rating(state)
        capacity = self._loan_approval(state, 1, 120, self._average_monthly_profit(state), self._portfolio_value(state))
        factors = self.credit_rating_factors(state)
        positives = [f"{factor['factor']}: {factor['impact']:+}" for factor in factors if int(factor["impact"]) > 0]
        negatives = [f"{factor['factor']}: {factor['impact']:+}" for factor in factors if int(factor["impact"]) < 0]
        return {
            "score": rating.score,
            "band": rating.band.value,
            "borrowing_capacity": capacity.max_loan_amount,
            "interest_rate_estimate": Loan.calculate_interest_rate(
                rating,
                self._group_balance_sheet(state).leverage_ratio,
                self._config.base_interest_rate,
            ),
            "positive_factors": positives or ["No major positive factors yet"],
            "negative_factors": negatives or ["No major negative factors"],
            "factors": factors,
        }

    def grant_debug_cash(self, state: GameState, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Cash grant must be greater than zero.")
        state.player.holding_company.add_cash(amount)
        self._add_alert(state, "Developer cash grant", f"{_format_money(amount)} added.", "Settings")

    def tax_summary(self, state: GameState) -> dict[str, int | float]:
        revenue = state.financials.income_statement.revenue.get("property_rent", 0)
        property_tax = state.financials.income_statement.expenses.get("property_tax", 0)
        stamp_duty = state.financials.income_statement.expenses.get("stamp_duty_paid", 0)
        interest = state.financials.income_statement.expenses.get("loan_interest", 0)
        deductible = sum(state.financials.income_statement.expenses.values()) - stamp_duty
        taxable_profit = max(0, revenue - deductible)
        corporate_tax = state.financials.income_statement.expenses.get("corporate_tax", 0)
        return {
            "gross_revenue": revenue,
            "deductible_expenses": deductible,
            "interest_deductions": interest,
            "taxable_profit": taxable_profit,
            "corporate_tax": corporate_tax,
            "property_tax": property_tax,
            "stamp_duty_paid": stamp_duty,
            "capital_gains_tax_rate": self._config.capital_gains_tax_rate,
            "net_profit_after_tax": revenue - sum(state.financials.income_statement.expenses.values()),
        }

    def tax_detail(self, state: GameState) -> dict[str, list[tuple[str, int | float | str]]]:
        summary = self.tax_summary(state)
        history = list(state.metadata.get("operating_history", []))
        monthly_tax_rows = [
            (
                str(item.get("date", "")),
                int(item.get("tax_paid", 0)),
                int(item.get("revenue", 0)),
                int(item.get("profit", 0)),
            )
            for item in history[-12:]
        ]
        annual_property_tax_projection = round(self._portfolio_value(state) * self._config.property_tax_annual_rate)
        projected_corporate_tax = round(max(0, self._average_monthly_profit(state) * 12) * self._config.corporate_tax_rate)
        total_tax_paid = int(summary["corporate_tax"]) + int(summary["property_tax"]) + int(summary["stamp_duty_paid"])
        effective_tax_rate = total_tax_paid / max(1, int(summary["gross_revenue"]))
        return {
            "summary": [
                ("Gross revenue", int(summary["gross_revenue"])),
                ("Deductible expenses", int(summary["deductible_expenses"])),
                ("Interest deductions", int(summary["interest_deductions"])),
                ("Taxable profit", int(summary["taxable_profit"])),
                ("Corporate tax paid", int(summary["corporate_tax"])),
                ("Property tax paid", int(summary["property_tax"])),
                ("Stamp duty paid", int(summary["stamp_duty_paid"])),
                ("Net profit after tax", int(summary["net_profit_after_tax"])),
            ],
            "rates": [
                ("Corporate tax rate", self._config.corporate_tax_rate),
                ("Property tax annual rate", self._config.property_tax_annual_rate),
                ("Stamp duty rate", self._config.stamp_duty_rate),
                ("Capital gains tax rate", self._config.capital_gains_tax_rate),
                ("Effective tax rate", effective_tax_rate),
            ],
            "forecast": [
                ("Projected annual property tax", annual_property_tax_projection),
                ("Projected annual corporate tax", projected_corporate_tax),
                ("Current quarterly taxable profit", int(state.metadata.get("quarter_taxable_profit", 0))),
                ("Next corporate tax month", self._next_corporate_tax_month(self._economy_date(state))),
                ("Filing status", "Current" if not bool(state.metadata.get("bankrupt", False)) else "Distressed"),
            ],
            "monthly_history": monthly_tax_rows,
        }

    def portfolio_by_city(self, state: GameState) -> list[dict[str, int | float | str]]:
        groups: dict[str, dict[str, int | float | str]] = {}
        for property_ in state.player_properties:
            context = state.world.city_context(property_.city_id)
            if context is None:
                continue
            _, country, _, city = context
            group = groups.setdefault(
                city.city_id,
                {
                    "city": city.name,
                    "country": country.name,
                    "Houses": 0,
                    "Apartments": 0,
                    "Offices": 0,
                    "Commercial": 0,
                    "Industrial": 0,
                    "portfolio_value": 0,
                    "revenue_month": 0,
                    "expenses_month": 0,
                    "profit_month": 0,
                    "yield_sum": 0.0,
                    "occupancy_sum": 0.0,
                    "count": 0,
                },
            )
            group[self._portfolio_bucket(property_)] = int(group[self._portfolio_bucket(property_)]) + 1
            value = property_.property_value(city)
            revenue = property_.monthly_rent(city)
            expenses = property_.monthly_maintenance(city)
            group["portfolio_value"] = int(group["portfolio_value"]) + value
            group["revenue_month"] = int(group["revenue_month"]) + revenue
            group["expenses_month"] = int(group["expenses_month"]) + expenses
            group["profit_month"] = int(group["profit_month"]) + revenue - expenses
            group["yield_sum"] = float(group["yield_sum"]) + (((revenue - expenses) * 12 / value) if value else 0.0)
            group["occupancy_sum"] = float(group["occupancy_sum"]) + property_.occupancy.rate
            group["count"] = int(group["count"]) + 1
        rows = []
        for group in groups.values():
            count = max(1, int(group.pop("count")))
            group["average_yield"] = float(group.pop("yield_sum")) / count
            group["average_occupancy"] = float(group.pop("occupancy_sum")) / count
            rows.append(group)
        return sorted(rows, key=lambda row: str(row["city"]))

    def city_market_rows(self, state: GameState) -> list[dict[str, int | float | str]]:
        rows = []
        owned_city_ids = {property_.city_id for property_ in state.player_properties}
        for country in state.world.countries:
            for city in country.cities:
                listings = self.property_listings(state, city.city_id)
                yields = [listing.annual_yield for listing in listings]
                competition = sum(1 for company in state.npc_companies for division in company.divisions for branch in division.branches if branch.city_id == city.city_id)
                rows.append(
                    {
                        "city": city.name,
                        "country": country.name,
                        "population": city.population,
                        "growth": city.growth_rate,
                        "demand": city.demand_score,
                        "average_yield": sum(yields) / len(yields),
                        "competition": competition,
                        "access_status": "Active" if city.city_id in owned_city_ids else "Open",
                    }
                )
        return rows

    def income_statement_lines(self, state: GameState) -> list[tuple[str, str, int]]:
        lines: list[tuple[str, str, int]] = []
        for name, value in sorted(state.financials.income_statement.revenue.items()):
            lines.append(("Revenue", name, value))
        for name, value in sorted(state.financials.income_statement.expenses.items()):
            lines.append(("Expense", name, value))
        lines.append(("Profit", "net_profit", state.financials.income_statement.profit))
        return lines

    def balance_sheet_lines(self, state: GameState) -> list[tuple[str, str, int]]:
        holding = state.player.holding_company
        property_value = self._portfolio_value(state)
        land_value = sum(parcel.purchase_price for parcel in state.player_land)
        construction_value = sum(project.total_cost for project in state.development_projects)
        company_cash = sum(company.cash for company in self._all_companies(holding.companies))
        company_debt = self._total_debt(state)
        total_assets = holding.cash + company_cash + property_value + land_value + construction_value
        return [
            ("Assets", "holding_cash", holding.cash),
            ("Assets", "company_cash", company_cash),
            ("Assets", "property_portfolio", property_value),
            ("Assets", "land_bank", land_value),
            ("Assets", "construction_in_progress", construction_value),
            ("Liabilities", "property_debt", company_debt),
            ("Equity", "owner_equity", total_assets - company_debt),
        ]

    def cash_flow_lines(self, state: GameState) -> list[tuple[str, str, int]]:
        lines: list[tuple[str, str, int]] = []
        for name, value in sorted(state.financials.cash_flow.operating.items()):
            lines.append(("Operating", name, value))
        for name, value in sorted(state.financials.cash_flow.investing.items()):
            lines.append(("Investing", name, value))
        for name, value in sorted(state.financials.cash_flow.financing.items()):
            lines.append(("Financing", name, value))
        lines.append(("Net", "net_cash_flow", state.financials.cash_flow.net_cash_flow))
        return lines

    def company_value(self, state: GameState) -> int:
        land_value = sum(parcel.purchase_price for parcel in state.player_land)
        construction_value = sum(project.total_cost for project in state.development_projects)
        return round(self._portfolio_value(state) + land_value + construction_value)

    def _process_development_day(self, state: GameState, current_date: date) -> None:
        completed: list[DevelopmentProject] = []
        for project in state.development_projects:
            project.advance_day()
            if project.complete:
                completed.append(project)

        for project in completed:
            state.development_projects.remove(project)
            parcel = self._find_owned_land(state, project.parcel_id)
            parcel.developed = True
            city = self._require_city(state, project.city_id)
            building_type = self._building_type_for_zoning(project.zoning)
            property_ = Property(
                name=project.building_name,
                building_type=building_type,
                city_id=project.city_id,
                condition=self._construction_company(project.construction_company_id).reliability,
                property_type=project.building_name,
                zoning=project.zoning.value,
                size_sqm=project.size_sqm,
                purchase_price=project.total_cost,
                expected_occupancy=min(0.94, 0.72 + city.demand_score / 450),
                monthly_revenue_override=project.expected_monthly_rent,
                monthly_expenses_override=project.expected_monthly_maintenance,
            )
            self._fill_tenants(property_, project.expected_monthly_rent, min(0.94, 0.72 + city.demand_score / 450))
            state.player_properties.append(property_)
            state.news_feed.add(
                f"Construction Completed On {project.building_name}",
                NewsCategory.REAL_ESTATE,
                current_date,
            )

    def _process_month(self, state: GameState, current_date: date) -> OperatingResult:
        starting_cash = state.player.holding_company.total_cash()
        starting_debt = self._total_debt(state)
        starting_rating = self.credit_rating(state).score
        self._process_city_managers(state, current_date)
        self._process_vacancy_events(state, current_date)
        income = {
            "Residential rent": 0,
            "Office rent": 0,
            "Commercial rent": 0,
            "Industrial rent": 0,
            "Asset sales": 0,
        }
        city_profit: dict[str, int] = {}
        rent = 0
        maintenance = 0
        property_tax = 0
        occupancy_total = 0.0
        yield_total = 0.0
        property_count = 0
        city_by_id = {city.city_id: city for city in state.world.cities}
        bonuses = self._research_bonuses(state)
        competition_by_city = self._city_competition_map(state)
        for property_ in state.player_properties:
            city = city_by_id.get(property_.city_id)
            if city is None:
                continue
            monthly_rent, actual_occupancy = self._monthly_property_rent(
                state,
                property_,
                city,
                current_date,
                bonuses,
                competition_by_city.get(city.city_id, 0),
            )
            monthly_maintenance = self._monthly_property_maintenance(property_, city, bonuses)
            property_value = property_.property_value(city)
            bucket = self._income_bucket(property_)
            income[bucket] = income.get(bucket, 0) + monthly_rent
            rent += monthly_rent
            maintenance += monthly_maintenance
            property_tax += round(property_value * self._config.property_tax_annual_rate / 12)
            city_profit[city.name] = city_profit.get(city.name, 0) + monthly_rent - monthly_maintenance
            occupancy_total += actual_occupancy
            value = max(property_value, 1)
            yield_total += ((monthly_rent - monthly_maintenance) * 12) / value
            property_count += 1

        payroll = self._monthly_payroll(state.player.holding_company)
        loan_interest, loan_principal, loan_payment = self._process_monthly_loans(state)
        operating_expenses = maintenance + property_tax + payroll + loan_interest
        net_before_corporate_tax = rent - operating_expenses
        self._add_cash_from_month(state, rent, maintenance + property_tax + payroll + loan_payment)
        self._record_financials(state, "property_rent", "property_maintenance", rent, maintenance)
        self._record_financials(state, "", "property_tax", 0, property_tax)
        self._record_financials(state, "", "executive_payroll", 0, payroll)
        self._record_financials(state, "", "loan_interest", 0, loan_interest)
        if loan_principal:
            state.financials.cash_flow.add_financing("scheduled_loan_principal", -loan_principal)

        taxable_profit = max(0, net_before_corporate_tax)
        state.metadata["quarter_taxable_profit"] = int(state.metadata.get("quarter_taxable_profit", 0)) + taxable_profit
        corporate_tax = 0
        if current_date.month in {1, 4, 7, 10}:
            corporate_tax = round(int(state.metadata.get("quarter_taxable_profit", 0)) * self._config.corporate_tax_rate)
            state.metadata["quarter_taxable_profit"] = 0
            if corporate_tax:
                self._pay_obligation(state, corporate_tax)
                self._record_financials(state, "", "corporate_tax", 0, corporate_tax)

        ending_cash = state.player.holding_company.total_cash()
        expenses = {
            "Loan repayments": loan_principal,
            "Interest": loan_interest,
            "Property tax": property_tax,
            "Maintenance": maintenance,
            "Construction costs": int(state.metadata.pop("month_construction_cost", 0)),
            "Operating costs": payroll,
        }
        result = OperatingResult(revenue=rent, expenses=operating_expenses + loan_principal + corporate_tax)
        report = {
            "type": "monthly",
            "date": current_date.isoformat(),
            "income": income,
            "expenses": expenses,
            "summary": {
                "Starting cash": starting_cash,
                "Ending cash": ending_cash,
                "Cash change": ending_cash - starting_cash,
                "Gross income": rent,
                "Total expenses": sum(expenses.values()) + corporate_tax,
                "Net profit": result.profit,
            },
        }
        self._queue_report(state, report)
        self._append_history(
            state,
            result,
            current_date,
            tax_paid=property_tax + corporate_tax,
            occupancy=(occupancy_total / property_count) if property_count else 0.0,
            average_yield=(yield_total / property_count) if property_count else 0.0,
            city_profit=city_profit,
        )
        ending_rating = self.credit_rating(state).score
        if ending_rating != starting_rating:
            self._add_alert(state, "Credit rating changed", f"{starting_rating} -> {ending_rating}", "Finance")
        if loan_payment:
            self._add_alert(state, "Loan payment due", f"{_format_money(loan_payment)} paid this month.", "Finance")
        if current_date.month in {1, 4, 7, 10}:
            self._queue_quarterly_report(state, current_date, starting_debt, starting_rating)
        return result

    def _process_monthly_loans(self, state: GameState) -> tuple[int, int, int]:
        interest_total = 0
        principal_total = 0
        payment_total = 0
        for company in self._all_companies(state.player.holding_company.companies):
            for loan in tuple(company.loans):
                if loan.status != "Current":
                    continue
                principal_before = loan.principal
                interest = round(loan.principal * loan.monthly_interest_rate)
                payment = loan.monthly_payment
                if payment and self._try_spend_company_then_group(state, company, payment):
                    actual_payment = loan.apply_monthly_payment()
                    principal_paid = principal_before - loan.principal
                    interest_total += max(0, actual_payment - principal_paid)
                    principal_total += principal_paid
                    payment_total += actual_payment
                elif payment:
                    loan.status = "Delinquent"
                    company.set_reputation(max(0, company.reputation - 4))
                    self._add_alert(state, "Loan payment missed", loan.name, "Finance")
                    state.news_feed.add("Loan Payment Missed", NewsCategory.FINANCE, self._economy_date(state))
                if loan.principal <= 0:
                    company.loans.remove(loan)
        return interest_total, principal_total, payment_total

    def _loan_approval(
        self,
        state: GameState,
        requested_loan_amount: int,
        term_months: int,
        projected_monthly_profit: int,
        collateral_value: int,
    ) -> LoanApproval:
        if requested_loan_amount <= 0:
            return LoanApproval(True, "No financing required.", 0, 0, 0.0, term_months, 0)
        if term_months < 12:
            return LoanApproval(False, "Loan term is too short.", 0, requested_loan_amount, 0.0, term_months, 0, ("Loan term is too short.",))

        rating = self.credit_rating(state)
        cash = state.player.holding_company.total_cash()
        portfolio_value = self._portfolio_value(state)
        land_value = sum(parcel.purchase_price for parcel in state.player_land)
        assets = portfolio_value + land_value + collateral_value + cash
        existing_debt = self._total_debt(state)
        bonuses = self._research_bonuses(state)
        if collateral_value:
            ltv_limit = round(collateral_value * self._config.max_ltv)
        else:
            ltv_limit = round((portfolio_value * 0.58) + (land_value * 0.38) + (cash * 1.25))
        debt_to_assets_limit = max(0, round((assets * self._config.max_debt_to_assets) - existing_debt))
        rating_ratio = max(0.0, (rating.score - self._config.min_credit_score) / max(1, 800 - self._config.min_credit_score))
        rating_multiplier = 0.25 + (rating_ratio * 1.5)
        rating_limit = round(((portfolio_value + land_value + collateral_value) * rating_multiplier) + (cash * 10))
        capacity_multiplier = 1 + bonuses["borrowing_capacity"]
        ltv_limit = round(ltv_limit * capacity_multiplier)
        debt_to_assets_limit = round(debt_to_assets_limit * capacity_multiplier)
        rating_limit = round(rating_limit * capacity_multiplier)
        balance_sheet = self._group_balance_sheet(state, extra_asset_value=collateral_value)
        quoted = Loan.quote(
            principal=requested_loan_amount,
            term_months=term_months,
            credit_rating=rating,
            balance_sheet=balance_sheet,
            base_rate=max(0.005, self._config.base_interest_rate - bonuses["loan_terms"]),
        )
        monthly_profit = max(projected_monthly_profit, self._average_monthly_profit(state))
        monthly_capacity = max(
            0,
            round(
                (max(0, monthly_profit) * 1.15)
                + (cash * 0.018)
                + (portfolio_value * 0.003)
                + (land_value * 0.0015)
                + (collateral_value * 0.002)
            ),
        )
        payment_capacity_limit = round(monthly_capacity * term_months * 0.82)
        max_loan_amount = max(
            0,
            round(
                min(
                    limit
                    for limit in (ltv_limit, debt_to_assets_limit, rating_limit, payment_capacity_limit)
                    if limit >= 0
                )
            ),
        )
        reasons = []
        if rating.score < self._config.min_credit_score:
            reasons.append("Credit rating too low.")
        if requested_loan_amount > ltv_limit:
            if collateral_value:
                reasons.append("Loan-to-value ratio is too high.")
            else:
                reasons.append("Requested loan exceeds available collateral and liquidity base.")
        if existing_debt > assets * self._config.max_debt_to_assets:
            reasons.append("Existing debt too high.")
        if requested_loan_amount > rating_limit:
            reasons.append("Credit rating and asset base do not support this loan size.")
        if requested_loan_amount > max_loan_amount:
            reasons.append("Requested loan exceeds bank limit.")
        if quoted.monthly_payment > monthly_capacity:
            reasons.append("Monthly repayment exceeds safe cashflow.")
        if reasons:
            return LoanApproval(
                False,
                reasons[0],
                max_loan_amount,
                requested_loan_amount,
                quoted.annual_interest_rate,
                term_months,
                quoted.monthly_payment,
                tuple(reasons),
            )
        return LoanApproval(
            True,
            "Approved.",
            max_loan_amount,
            requested_loan_amount,
            quoted.annual_interest_rate,
            term_months,
            quoted.monthly_payment,
            ("Approved.",),
        )

    def _property_from_listing(self, listing: PropertyListing, purchase_price: int | None = None) -> Property:
        property_ = Property(
            name=listing.name,
            building_type=self._building_type_for_zoning(listing.zoning),
            city_id=listing.city_id,
            property_id=listing.listing_id,
            condition=listing.condition,
            property_type=listing.property_type,
            zoning=listing.zoning.value,
            size_sqm=listing.size_sqm,
            purchase_price=purchase_price if purchase_price is not None else listing.asking_price,
            expected_occupancy=listing.occupancy_rate,
            monthly_revenue_override=listing.monthly_revenue,
            monthly_expenses_override=listing.monthly_expenses,
        )
        self._fill_tenants(property_, listing.monthly_revenue, listing.occupancy_rate)
        return property_

    def _fill_tenants(self, property_: Property, monthly_rent: int, occupancy_rate: float) -> None:
        property_.actual_occupancy = max(0.0, min(1.0, occupancy_rate))
        tenant_count = max(1, min(property_.building_type.tenant_capacity, round(property_.building_type.tenant_capacity * occupancy_rate)))
        if property_.building_type.tenant_capacity > 24:
            return
        for tenant_index in range(tenant_count):
            property_.add_tenant(Tenant(name=f"Tenant {tenant_index + 1}", monthly_rent=round(monthly_rent / tenant_count)))

    def _advance_economy_date(self, state: GameState) -> date:
        current = self._economy_date(state) + timedelta(days=1)
        state.metadata["economy_date"] = current.isoformat()
        return current

    def _economy_date(self, state: GameState) -> date:
        return date.fromisoformat(str(state.metadata.get("economy_date", state.clock.current_date.isoformat())))

    def _add_cash_from_month(self, state: GameState, revenue: int, cash_expenses: int) -> None:
        net = revenue - cash_expenses
        if net >= 0:
            state.player.holding_company.add_cash(net)
        else:
            self._pay_obligation(state, abs(net))

    def _pay_obligation(self, state: GameState, amount: int) -> None:
        if amount <= 0:
            return
        if self._try_spend_group_cash(state, amount):
            return
        self._wipe_group_cash(state)
        state.metadata["bankrupt"] = True
        self._add_alert(state, "Bankruptcy warning", "Cash could not cover required obligations.", "Finance")
        state.news_feed.add("Property Group Enters Distress", NewsCategory.FINANCE, self._economy_date(state))

    def _wipe_group_cash(self, state: GameState) -> None:
        holding = state.player.holding_company
        holding.cash = 0
        for company in self._all_companies(holding.companies):
            company.cash = 0

    def _monthly_property_rent(
        self,
        state: GameState,
        property_: Property,
        city: City,
        current_date: date,
        bonuses: dict[str, float] | None = None,
        city_competition: int | None = None,
    ) -> tuple[int, float]:
        bonuses = bonuses or self._research_bonuses(state)
        random = Random(f"rent:{property_.property_id}:{current_date.isoformat()}")
        previous_occupancy = property_.occupancy.rate
        event_modifier = self._vacancy_modifier(state, city.city_id, property_.zoning or "")
        competition = self._city_competition(state, city.city_id) if city_competition is None else city_competition
        expected = property_.expected_occupancy if property_.expected_occupancy is not None else property_.building_type.target_occupancy
        demand_support = (city.demand_score - 70) / 500
        quality_support = (property_.condition - 0.82) * 0.16
        competition_penalty = min(0.12, competition * 0.012)
        market_variation = random.uniform(-0.08, 0.08)
        target_occupancy = max(
            0.35,
            min(
                0.99,
                expected
                + demand_support
                + quality_support
                + event_modifier
                + market_variation
                + bonuses["occupancy"]
                + max(0.0, -bonuses["vacancy_risk"] * 0.35)
                - competition_penalty,
            ),
        )
        actual_occupancy = max(0.30, min(0.99, previous_occupancy + ((target_occupancy - previous_occupancy) * 0.48)))
        property_.actual_occupancy = actual_occupancy
        potential_rent = self._property_potential_rent(property_, city)
        value_multiplier = 0.9 + (city.property_multiplier * 0.08)
        volatility = random.uniform(0.94, 1.06)
        rent = round(potential_rent * actual_occupancy * volatility * value_multiplier * (1 + bonuses["rent"]))
        return max(0, rent), actual_occupancy

    def _property_potential_rent(self, property_: Property, city: City) -> int:
        if property_.monthly_revenue_override is not None:
            expected = property_.expected_occupancy if property_.expected_occupancy else max(property_.occupancy.rate, 0.5)
            return round(property_.monthly_revenue_override / max(expected, 0.35))
        if property_.tenants:
            return round(sum(tenant.monthly_rent for tenant in property_.tenants) / max(property_.occupancy.rate, 0.35))
        return property_.building_type.city_monthly_rent(city)

    def _set_property_occupancy(self, property_: Property, city: City, occupancy_rate: float) -> None:
        property_.actual_occupancy = max(0.0, min(1.0, occupancy_rate))
        tenant_count = max(1, min(property_.building_type.tenant_capacity, round(property_.building_type.tenant_capacity * occupancy_rate)))
        if property_.building_type.tenant_capacity > 24:
            return
        potential_rent = self._property_potential_rent(property_, city)
        property_.tenants.clear()
        rent_per_tenant = max(1, round((potential_rent * occupancy_rate) / tenant_count))
        for tenant_index in range(tenant_count):
            property_.add_tenant(Tenant(name=f"Tenant {tenant_index + 1}", monthly_rent=rent_per_tenant))

    def _vacancy_modifier(self, state: GameState, city_id: str, zoning: str) -> float:
        modifiers = dict(state.metadata.get("vacancy_modifiers", {}))
        return float(modifiers.get(f"{city_id}:{zoning}", 0.0)) + float(modifiers.get(f"{city_id}:*", 0.0))

    def _process_vacancy_events(self, state: GameState, current_date: date) -> None:
        modifiers = {
            key: {"months": int(value.get("months", 0)) - 1, "impact": float(value.get("impact", 0.0))}
            for key, value in dict(state.metadata.get("vacancy_events", {})).items()
        }
        modifiers = {key: value for key, value in modifiers.items() if int(value["months"]) > 0}
        if state.player_properties:
            random = Random(f"vacancy-event:{state.world_id}:{current_date.year}:{current_date.month}")
            vacancy_risk = max(0.02, 0.12 + self._research_bonuses(state)["vacancy_risk"])
            if random.random() < vacancy_risk:
                property_ = random.choice(state.player_properties)
                city = self._require_city(state, property_.city_id)
                event_name, impact, zoning = random.choice(
                    (
                        ("Major Tenant Leaves", -0.12, property_.zoning or "*"),
                        ("Corporate Downsizing", -0.09, Zoning.OFFICE.value),
                        ("Retail Vacancy Increase", -0.08, Zoning.COMMERCIAL.value),
                        ("Office Demand Surge", 0.07, Zoning.OFFICE.value),
                        ("Student Housing Boom", 0.06, Zoning.RESIDENTIAL.value),
                    )
                )
                key = f"{city.city_id}:{zoning}"
                modifiers[key] = {"months": 3, "impact": impact}
                self._add_alert(state, event_name, f"{self._city_name(state, city.city_id)} occupancy impact {impact:+.0%}.", "Vacancy")
                state.news_feed.add(f"{event_name} In {city.name}", NewsCategory.MARKET, current_date)
        state.metadata["vacancy_events"] = modifiers
        state.metadata["vacancy_modifiers"] = {key: value["impact"] for key, value in modifiers.items()}

    def _process_city_managers(self, state: GameState, current_date: date) -> None:
        managers = self._city_managers(state)
        if not managers:
            return
        month_key = current_date.strftime("%Y-%m")
        changed = False
        for city_id, manager in list(managers.items()):
            if manager.budget_month != month_key:
                manager = CityManagerProfile(**{**manager.to_dict(), "month_spent": 0, "budget_month": month_key})
            city = state.world.get_city(city_id)
            if city is None:
                managers[city_id] = CityManagerProfile(**{**manager.to_dict(), "status": "City unavailable"})
                changed = True
                continue
            effective_budget = round(manager.monthly_budget * (1 + self._research_bonuses(state)["manager_effectiveness"]))
            remaining_budget = max(0, effective_budget - manager.month_spent)
            listings = [
                listing
                for listing in self.property_listings(state, city_id)
                if listing.listing_id not in {property_.property_id for property_ in state.player_properties}
                and listing.rarity is not DealRarity.LANDMARK
                and listing.zoning.value in manager.allowed_property_types
                and listing.annual_yield >= manager.min_yield
                and listing.asking_price <= manager.max_property_price
            ]
            listings.sort(key=lambda listing: self._manager_listing_score(listing, manager.aggressiveness), reverse=True)
            purchased = False
            for listing in listings:
                quote = self.quote_property_purchase(state, listing.listing_id, deposit_percent=1.0)
                if quote.cash_required > remaining_budget:
                    continue
                if state.player.holding_company.total_cash() - quote.cash_required < manager.cash_reserve_requirement:
                    continue
                self.buy_property_listing(state, listing.listing_id, deposit_percent=1.0)
                invested = manager.month_spent + quote.cash_required
                managers[city_id] = CityManagerProfile(
                    manager_id=manager.manager_id,
                    name=manager.name,
                    city_id=manager.city_id,
                    monthly_budget=manager.monthly_budget,
                    min_yield=manager.min_yield,
                    max_property_price=manager.max_property_price,
                    allowed_property_types=manager.allowed_property_types,
                    aggressiveness=manager.aggressiveness,
                    cash_reserve_requirement=manager.cash_reserve_requirement,
                    properties_purchased=manager.properties_purchased + 1,
                    capital_invested=manager.capital_invested + quote.cash_required,
                    yield_achieved_sum=manager.yield_achieved_sum + listing.annual_yield,
                    status=f"Purchased {listing.name}",
                    month_spent=invested,
                    budget_month=month_key,
                )
                self._add_alert(state, "City manager purchase", f"{manager.name} purchased {listing.name}.", "Management")
                purchased = True
                changed = True
                break
            if not purchased:
                managers[city_id] = CityManagerProfile(**{**manager.to_dict(), "status": "Monitoring deals", "month_spent": manager.month_spent, "budget_month": month_key})
                changed = True
        if changed:
            self._save_city_managers(state, managers)

    def _manager_listing_score(self, listing: PropertyListing, aggressiveness: str) -> float:
        if aggressiveness == "Conservative":
            return (listing.annual_yield * 100) - (listing.asking_price / 1_000_000)
        if aggressiveness == "Aggressive":
            return (listing.annual_yield * 140) + (listing.demand_multiplier * 8) + (listing.size_sqm / 4000)
        return (listing.annual_yield * 120) + (listing.demand_multiplier * 5)

    def _city_competition(self, state: GameState, city_id: str) -> int:
        return sum(
            1
            for company in state.npc_companies
            for division in company.divisions
            for branch in division.branches
            if branch.city_id == city_id
        )

    def _city_competition_map(self, state: GameState) -> dict[str, int]:
        competition: dict[str, int] = {}
        for company in state.npc_companies:
            for division in company.divisions:
                for branch in division.branches:
                    if branch.city_id:
                        competition[branch.city_id] = competition.get(branch.city_id, 0) + 1
        return competition

    def _monthly_property_maintenance(
        self,
        property_: Property,
        city: City,
        bonuses: dict[str, float] | None = None,
    ) -> int:
        base = property_.monthly_maintenance(city)
        bonuses = bonuses or {
            "maintenance": 0.0,
            "operating_margin": 0.0,
        }
        return round(base * max(0.45, 1 - bonuses["maintenance"] - bonuses["operating_margin"]))

    def _record_financials(self, state: GameState, revenue_line: str, expense_line: str, revenue: int, expenses: int) -> None:
        if revenue_line and revenue:
            state.financials.income_statement.add_revenue(revenue_line, revenue)
            state.financials.cash_flow.add_operating(revenue_line, revenue)
        if expense_line and expenses:
            state.financials.income_statement.add_expense(expense_line, expenses)
            state.financials.cash_flow.add_operating(expense_line, -expenses)

    def _queue_report(self, state: GameState, report: dict[str, Any]) -> None:
        reports = list(state.metadata.get("pending_reports", []))
        reports.append(report)
        state.metadata["pending_reports"] = reports[-6:]
        archive = list(state.metadata.get("reports", []))
        archive.append(report)
        state.metadata["reports"] = archive[-36:]

    def _queue_quarterly_report(self, state: GameState, current_date: date, starting_debt: int, starting_rating: int) -> None:
        history = list(state.metadata.get("operating_history", []))[-3:]
        revenue = sum(int(item.get("revenue", 0)) for item in history)
        profit = sum(int(item.get("profit", 0)) for item in history)
        city_scores: dict[str, int] = {}
        for item in history:
            for city, value in dict(item.get("city_profit", {})).items():
                city_scores[str(city)] = city_scores.get(str(city), 0) + int(value)
        best_city = max(city_scores, key=city_scores.get) if city_scores else "None"
        worst_city = min(city_scores, key=city_scores.get) if city_scores else "None"
        current_occupancy = self._portfolio_occupancy(state)
        current_rating = self.credit_rating(state).score
        report = {
            "type": "quarterly",
            "date": current_date.isoformat(),
            "summary": {
                "Revenue": revenue,
                "Profit": profit,
                "Debt change": self._total_debt(state) - int(state.metadata.get("quarter_start_debt", starting_debt)),
                "Tax paid": sum(int(item.get("tax_paid", 0)) for item in history),
                "Portfolio growth": self._portfolio_value(state) - int(state.metadata.get("quarter_start_portfolio_value", 0)),
                "Best city": best_city,
                "Worst city": worst_city,
                "Occupancy change": current_occupancy - float(state.metadata.get("quarter_start_occupancy", current_occupancy)),
                "Credit rating change": current_rating - int(state.metadata.get("quarter_start_credit_rating", starting_rating)),
            },
        }
        self._queue_report(state, report)
        state.metadata["quarter_start_debt"] = self._total_debt(state)
        state.metadata["quarter_start_portfolio_value"] = self._portfolio_value(state)
        state.metadata["quarter_start_occupancy"] = current_occupancy
        state.metadata["quarter_start_credit_rating"] = current_rating

    def _add_alert(self, state: GameState, title: str, message: str, category: str) -> None:
        alerts = list(state.metadata.get("alerts", []))
        alerts.insert(
            0,
            {
                "date": self._economy_date(state).isoformat(),
                "category": category,
                "title": title,
                "message": message,
            },
        )
        state.metadata["alerts"] = alerts[:80]

    def _income_bucket(self, property_: Property) -> str:
        zoning = property_.zoning or ""
        property_type = (property_.property_type or property_.building_type.name).lower()
        if zoning == Zoning.OFFICE.value:
            return "Office rent"
        if zoning == Zoning.COMMERCIAL.value or zoning == Zoning.HOTEL.value or zoning == Zoning.LANDMARK.value:
            return "Commercial rent"
        if zoning == Zoning.INDUSTRIAL.value:
            return "Industrial rent"
        if "house" in property_type or "residential" in property_type or "apartment" in property_type:
            return "Residential rent"
        return "Commercial rent"

    def _portfolio_bucket(self, property_: Property) -> str:
        zoning = property_.zoning or ""
        property_type = (property_.property_type or property_.building_type.name).lower()
        if zoning == Zoning.OFFICE.value:
            return "Offices"
        if zoning == Zoning.COMMERCIAL.value or zoning == Zoning.HOTEL.value or zoning == Zoning.LANDMARK.value:
            return "Commercial"
        if zoning == Zoning.INDUSTRIAL.value:
            return "Industrial"
        if "house" in property_type or "estate" in property_type:
            return "Houses"
        return "Apartments"

    def _portfolio_occupancy(self, state: GameState) -> float:
        if not state.player_properties:
            return 0.0
        return sum(property_.occupancy.rate for property_ in state.player_properties) / len(state.player_properties)

    def _average_company_reputation(self, state: GameState) -> float:
        companies = self._all_companies(state.player.holding_company.companies)
        if not companies:
            return state.player.holding_company.reputation
        return sum(company.reputation for company in companies) / len(companies)

    def _completed_research(self, state: GameState) -> set[str]:
        return {str(item) for item in state.metadata.get("completed_research", [])}

    def _city_managers(self, state: GameState) -> dict[str, CityManagerProfile]:
        return {
            str(city_id): CityManagerProfile.from_dict(dict(payload))
            for city_id, payload in dict(state.metadata.get("city_managers", {})).items()
        }

    def _save_city_managers(self, state: GameState, managers: dict[str, CityManagerProfile]) -> None:
        state.metadata["city_managers"] = {
            city_id: manager.to_dict()
            for city_id, manager in managers.items()
        }

    def _mega_projects(self, state: GameState) -> dict[str, MegaProjectOpportunity]:
        return {
            str(project_id): MegaProjectOpportunity.from_dict(dict(payload))
            for project_id, payload in dict(state.metadata.get("mega_projects", {})).items()
        }

    def _save_mega_projects(self, state: GameState, projects: dict[str, MegaProjectOpportunity]) -> None:
        state.metadata["mega_projects"] = {
            project_id: project.to_dict()
            for project_id, project in projects.items()
        }

    def _create_mega_project(self, state: GameState, current_date: date) -> MegaProjectOpportunity:
        random = Random(f"mega-create:{state.world_id}:{current_date.isoformat()}:{len(self._mega_projects(state))}")
        city = random.choice(tuple(sorted(state.world.cities, key=lambda item: item.demand_score, reverse=True))[:12])
        project_type = random.choice(
            (
                "Waterfront Redevelopment",
                "New Financial District",
                "International Airport Expansion",
                "Technology Campus",
                "Luxury Coastal Resort",
                "Mixed-Use Mega Development",
                "Business District Redevelopment",
            )
        )
        cost = random.randint(1_000_000_000, 40_000_000_000)
        duration = random.randint(900, 2200)
        risk_roll = random.random()
        risk_rating = "Low" if risk_roll < 0.25 else "Medium" if risk_roll < 0.68 else "High"
        demand = 0.75 + (city.demand_score / 100) * 0.55
        revenue = round(cost * random.uniform(0.006, 0.012) * demand)
        profit = round(revenue * random.uniform(0.38, 0.58))
        return MegaProjectOpportunity(
            project_id=f"mega_{uuid4().hex[:10]}",
            name=f"{city.name} {project_type}",
            city_id=city.city_id,
            project_type=project_type,
            estimated_cost=cost,
            construction_days=duration,
            expected_revenue=revenue,
            expected_profit=profit,
            risk_rating=risk_rating,
            prestige_reward=random.randint(8, 32),
            days_remaining=540,
        )

    def _process_mega_project_day(self, state: GameState, current_date: date) -> None:
        projects = self._mega_projects(state)
        if not projects:
            return
        changed = False
        for project_id, project in list(projects.items()):
            if project.status in {"Available", "Delayed"}:
                remaining = project.days_remaining - 1
                if remaining <= 0:
                    projects.pop(project_id)
                else:
                    projects[project_id] = MegaProjectOpportunity(**{**project.to_dict(), "days_remaining": remaining})
                changed = True
                continue
            if project.status != "Proceeding":
                continue
            random = Random(f"mega-day:{project.project_id}:{current_date.isoformat()}")
            risk_modifier = max(0.0, -self._research_bonuses(state)["mega_risk"])
            delay_chance = max(0.0002, {"Low": 0.0006, "Medium": 0.0012, "High": 0.0022}.get(project.risk_rating, 0.0012) - risk_modifier / 100)
            cost_chance = max(0.0001, {"Low": 0.0004, "Medium": 0.0009, "High": 0.0018}.get(project.risk_rating, 0.0009) - risk_modifier / 120)
            days_remaining = project.days_remaining - 1
            estimated_cost = project.estimated_cost
            if random.random() < delay_chance:
                days_remaining += random.randint(20, 80)
                self._add_alert(state, "Mega project delay", project.name, "Mega Project")
            if random.random() < cost_chance:
                overrun = round(estimated_cost * random.uniform(0.01, 0.035))
                estimated_cost += overrun
                self._pay_obligation(state, overrun)
                state.financials.cash_flow.add_investing("mega_project_overrun", -overrun)
                self._add_alert(state, "Mega project cost overrun", f"{project.name}: {_format_money(overrun)}.", "Mega Project")
            if days_remaining <= 0:
                self._complete_mega_project(state, project, estimated_cost, current_date)
                projects[project_id] = MegaProjectOpportunity(**{**project.to_dict(), "status": "Completed", "days_remaining": 0, "estimated_cost": estimated_cost})
            else:
                projects[project_id] = MegaProjectOpportunity(**{**project.to_dict(), "days_remaining": days_remaining, "estimated_cost": estimated_cost})
            changed = True
        if changed:
            self._save_mega_projects(state, projects)

    def _complete_mega_project(
        self,
        state: GameState,
        project: MegaProjectOpportunity,
        final_cost: int,
        current_date: date,
    ) -> None:
        city = self._require_city(state, project.city_id)
        risk_penalty = {"Low": 0.98, "Medium": 0.9, "High": 0.78}.get(project.risk_rating, 0.9)
        property_ = Property(
            name=project.name,
            building_type=self._building_type_for_zoning(Zoning.LANDMARK),
            city_id=project.city_id,
            property_id=f"{project.project_id}_asset",
            condition=0.9,
            property_type=project.project_type,
            zoning=Zoning.LANDMARK.value,
            size_sqm=max(80_000, round(final_cost / max(1, city.property_multiplier * 9000))),
            purchase_price=final_cost,
            expected_occupancy=max(0.62, min(0.95, (0.72 + city.demand_score / 450) * risk_penalty)),
            monthly_revenue_override=round(project.expected_revenue * risk_penalty),
            monthly_expenses_override=max(0, round((project.expected_revenue - project.expected_profit) * (1.08 if project.risk_rating == "High" else 1.0))),
        )
        self._fill_tenants(property_, property_.monthly_revenue_override or project.expected_revenue, property_.expected_occupancy or 0.82)
        state.player_properties.append(property_)
        state.player.holding_company.reputation = min(100.0, state.player.holding_company.reputation + project.prestige_reward / 2)
        state.metadata["prestige"] = int(state.metadata.get("prestige", 0)) + project.prestige_reward
        self._add_alert(state, "Mega project complete", f"{project.name} added to portfolio.", "Mega Project")
        state.news_feed.add(f"Mega Project Completed: {project.name}", NewsCategory.REAL_ESTATE, current_date)

    def _research_bonuses(self, state: GameState) -> dict[str, float]:
        completed = self._completed_research(state)
        bonuses = {
            "rent": 0.0,
            "occupancy": 0.0,
            "maintenance": 0.0,
            "construction_time": 0.0,
            "construction_cost": 0.0,
            "loan_terms": 0.0,
            "credit": 0.0,
            "planning_score": 0.0,
            "planning_threshold": 0.0,
            "operating_margin": 0.0,
            "vacancy_risk": 0.0,
            "borrowing_capacity": 0.0,
            "manager_effectiveness": 0.0,
            "acquisition_discount": 0.0,
            "mega_risk": 0.0,
            "city_manager_unlock": 0.0,
        }
        for node in self.RESEARCH_NODES:
            if node.node_id not in completed:
                continue
            for effect in node.effects:
                bonuses[effect.key] = bonuses.get(effect.key, 0.0) + effect.amount
        return bonuses

    def _negotiate(
        self,
        state: GameState,
        target_id: str,
        target_type: str,
        asking_price: int,
        offer_amount: int,
        days_remaining: int,
    ) -> NegotiationResult:
        if offer_amount <= 0:
            raise ValueError("Offer must be greater than zero.")
        negotiation_id = f"{target_type}_{target_id}"
        previous_negotiation = dict(state.metadata.get("negotiations", {})).get(negotiation_id, {})
        previous_counter = previous_negotiation.get("counteroffer")
        if previous_counter and offer_amount >= int(previous_counter):
            status = "Accepted"
            response = "Accept"
            counteroffer = None
            message = f"Seller accepted at {_format_money(offer_amount)}."
            negotiation = NegotiationResult(
                negotiation_id=negotiation_id,
                target_id=target_id,
                target_type=target_type,
                player_offer=offer_amount,
                seller_response=response,
                status=status,
                counteroffer=counteroffer,
                message=message,
            )
            negotiations = dict(state.metadata.get("negotiations", {}))
            negotiations[negotiation.negotiation_id] = {
                "target_id": target_id,
                "target_type": target_type,
                "player_offer": offer_amount,
                "seller_response": response,
                "status": status,
                "counteroffer": counteroffer,
                "message": message,
            }
            state.metadata["negotiations"] = negotiations
            return negotiation
        ratio = offer_amount / asking_price
        pressure = 0.02 if days_remaining < 20 else 0.0
        proof_needed = ratio >= 0.82 and state.player.holding_company.total_cash() < offer_amount * 0.25
        if ratio >= 0.96 - pressure:
            status = "Accepted"
            response = "Accept"
            counteroffer = None
            message = "Seller accepted the offer."
        elif proof_needed:
            status = "Proof Requested"
            response = "Request proof of financing"
            counteroffer = None
            message = "Seller wants proof of financing before continuing."
        elif ratio >= 0.86 - pressure:
            status = "Countered"
            response = "Counteroffer"
            counteroffer = round(asking_price * 0.94)
            message = f"Seller countered at {_format_money(counteroffer)}."
        elif ratio < 0.72:
            status = "Withdrawn"
            response = "Withdraw deal"
            counteroffer = None
            message = "Seller withdrew after a very low offer."
        else:
            status = "Rejected"
            response = "Reject"
            counteroffer = None
            message = "Seller rejected the offer."
        negotiation = NegotiationResult(
            negotiation_id=negotiation_id,
            target_id=target_id,
            target_type=target_type,
            player_offer=offer_amount,
            seller_response=response,
            status=status,
            counteroffer=counteroffer,
            message=message,
        )
        negotiations = dict(state.metadata.get("negotiations", {}))
        negotiations[negotiation.negotiation_id] = {
            "target_id": target_id,
            "target_type": target_type,
            "player_offer": offer_amount,
            "seller_response": response,
            "status": status,
            "counteroffer": counteroffer,
            "message": message,
        }
        state.metadata["negotiations"] = negotiations
        return negotiation

    def _append_history(
        self,
        state: GameState,
        result: OperatingResult,
        current_date: date,
        tax_paid: int,
        occupancy: float,
        average_yield: float,
        city_profit: dict[str, int],
    ) -> None:
        if result.revenue == 0 and result.expenses == 0:
            return
        history = list(state.metadata.get("operating_history", []))
        history.append(
            {
                "date": current_date.isoformat(),
                "revenue": result.revenue,
                "profit": result.profit,
                "cash": state.player.holding_company.total_cash(),
                "debt": self._total_debt(state),
                "company_value": self.company_value(state),
                "portfolio_value": self._portfolio_value(state),
                "credit_rating": self.credit_rating(state).score,
                "occupancy": occupancy,
                "yield": average_yield,
                "tax_paid": tax_paid,
                "construction_pipeline": sum(project.total_cost for project in state.development_projects),
                "city_profit": city_profit,
            }
        )
        state.metadata["operating_history"] = history[-90:]

    def _portfolio_value(self, state: GameState) -> int:
        return sum(
            property_.property_value(city)
            for property_ in state.player_properties
            if (city := state.world.get_city(property_.city_id)) is not None
        )

    def _average_monthly_profit(self, state: GameState) -> int:
        history = [int(item.get("profit", 0)) for item in state.metadata.get("operating_history", []) if int(item.get("revenue", 0)) > 0]
        if history:
            return round(sum(history[-6:]) / min(len(history), 6))
        projected = 0
        for property_ in state.player_properties:
            city = state.world.get_city(property_.city_id)
            if city is not None:
                projected += property_.monthly_net_income(city)
        return projected

    def _group_balance_sheet(self, state: GameState, extra_asset_value: int = 0) -> BalanceSheet:
        assets = state.player.holding_company.total_cash() + self._portfolio_value(state) + sum(parcel.purchase_price for parcel in state.player_land) + extra_asset_value
        liabilities = self._total_debt(state)
        return BalanceSheet(assets={"group_assets": max(assets, 0)}, liabilities={"property_debt": liabilities})

    def _total_debt(self, state: GameState) -> int:
        return sum(company.total_debt for company in self._all_companies(state.player.holding_company.companies))

    def _monthly_payroll(self, holding: HoldingCompany) -> int:
        return round(sum(executive.salary for company in self._all_companies(holding.companies) for executive in company.executives) / 12)

    def _find_property_listing(self, state: GameState, listing_id: str) -> PropertyListing:
        city_id = "_".join(listing_id.split("_")[:-2])
        cities = (state.world.get_city(city_id),) if state.world.get_city(city_id) is not None else state.world.cities
        for city in cities:
            if city is None:
                continue
            listing = self._property_marketplace.get_listing(city, listing_id)
            if listing is not None:
                return listing
        raise ValueError(f"Unknown property listing: {listing_id}")

    def _find_land_listing(self, state: GameState, listing_id: str) -> LandListing:
        city_id = "_".join(listing_id.split("_")[:-2])
        cities = (state.world.get_city(city_id),) if state.world.get_city(city_id) is not None else state.world.cities
        for city in cities:
            if city is None:
                continue
            listing = self._land_marketplace.get_listing(city, listing_id)
            if listing is not None:
                return listing
        raise ValueError(f"Unknown land listing: {listing_id}")

    def _find_owned_land(self, state: GameState, parcel_id: str) -> LandParcel:
        parcel = next((parcel for parcel in state.player_land if parcel.parcel_id == parcel_id), None)
        if parcel is None:
            raise ValueError(f"Unknown land parcel: {parcel_id}")
        return parcel

    def _construction_company(self, construction_company_id: str) -> ConstructionCompany:
        company = next((company for company in self._construction_companies if company.company_id == construction_company_id), None)
        if company is None:
            raise ValueError(f"Unknown construction company: {construction_company_id}")
        return company

    def _development_option(self, option_id: str) -> DevelopmentOption:
        option = next((option for option in self._development_options if option.option_id == option_id), None)
        if option is None:
            raise ValueError(f"Unknown development option: {option_id}")
        return option

    def _company_for_loan(self, state: GameState, loan_id: str) -> Company:
        for company in self._all_companies(state.player.holding_company.companies):
            if any(loan.loan_id == loan_id for loan in company.loans):
                return company
        raise ValueError(f"Loan not found: {loan_id}")

    def _spend_group_cash(self, state: GameState, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cash spending cannot be negative.")
        if not self._try_spend_group_cash(state, amount):
            raise ValueError(f"Not enough cash. Available {_format_money(state.player.holding_company.total_cash())}, required {_format_money(amount)}.")

    def _try_spend_group_cash(self, state: GameState, amount: int) -> bool:
        holding = state.player.holding_company
        if amount > holding.total_cash():
            return False
        remaining = amount
        holding_payment = min(holding.cash, remaining)
        if holding_payment:
            holding.spend_cash(holding_payment)
            remaining -= holding_payment
        for company in self._all_companies(holding.companies):
            if remaining <= 0:
                break
            company_payment = min(company.cash, remaining)
            if company_payment:
                company.spend_cash(company_payment)
                remaining -= company_payment
        return True

    def _spend_company_then_group(self, state: GameState, company: Company, amount: int) -> None:
        if not self._try_spend_company_then_group(state, company, amount):
            raise ValueError(f"Not enough cash. Available {_format_money(state.player.holding_company.total_cash())}, required {_format_money(amount)}.")

    def _try_spend_company_then_group(self, state: GameState, company: Company, amount: int) -> bool:
        if amount > state.player.holding_company.total_cash():
            return False
        company_payment = min(company.cash, amount)
        if company_payment:
            company.spend_cash(company_payment)
        remaining = amount - company_payment
        if remaining:
            return self._try_spend_group_cash(state, remaining)
        return True

    def _require_property_game(self, state: GameState) -> None:
        starting_industry = state.metadata.get("starting_industry", "real_estate")
        if starting_industry != "real_estate":
            raise ValueError("Only Real Estate is active in Property Empire Simulator.")

    def _require_city(self, state: GameState, city_id: str) -> City:
        city = state.world.get_city(city_id)
        if city is None:
            raise ValueError(f"Unknown city: {city_id}")
        return city

    def _city_name(self, state: GameState, city_id: str) -> str:
        city = state.world.get_city(city_id)
        return city.name if city is not None else city_id

    def _building_type_for_zoning(self, zoning: Zoning | str) -> BuildingType:
        zoning_value = zoning if isinstance(zoning, Zoning) else Zoning(str(zoning))
        mapping = {
            Zoning.RESIDENTIAL: "apartment_complex",
            Zoning.OFFICE: "small_office",
            Zoning.COMMERCIAL: "retail_block",
            Zoning.INDUSTRIAL: "industrial_warehouse",
            Zoning.HOTEL: "retail_block",
            Zoning.LANDMARK: "office_tower",
        }
        return self._real_estate.building_types[mapping[zoning_value]]

    def _deal_sort_value(self, listing: PropertyListing, key_name: str) -> int | float:
        if key_name == "price":
            return listing.asking_price
        if key_name == "size":
            return listing.size_sqm
        if key_name == "yield":
            return listing.annual_yield
        if key_name == "demand":
            return listing.demand_multiplier
        if key_name == "days_remaining":
            return -listing.days_remaining
        return listing.annual_yield

    def _next_corporate_tax_month(self, current_date: date) -> str:
        months = (1, 4, 7, 10)
        for month in months:
            if current_date.month < month:
                return date(current_date.year, month, 1).strftime("%B %Y")
        return date(current_date.year + 1, 1, 1).strftime("%B %Y")

    def _company_id(self, company_name: str) -> str:
        base = "".join(character.lower() if character.isalnum() else "_" for character in company_name)
        clean = "_".join(part for part in base.split("_") if part)
        return f"{clean or 'company'}_{uuid4().hex[:8]}"

    def _all_companies(self, companies: list[Company]) -> list[Company]:
        flattened: list[Company] = []
        for company in companies:
            flattened.append(company)
            flattened.extend(self._all_companies(company.subsidiaries))
        return flattened


def _format_money(value: int | float) -> str:
    return f"${round(value):,}"
