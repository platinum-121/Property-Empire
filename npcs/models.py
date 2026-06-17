# npcs/models.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass

from companies.models import Asset, Branch, Company, Division, Executive, NPCCompanyTrait, SkillRatings
from world.system import WorldSystem


@dataclass(frozen=True, slots=True)
class NPCSimulationReport:
    income_earned: int = 0
    branches_opened: int = 0
    assets_collected: int = 0
    loans_taken: int = 0
    executives_hired: int = 0


class NPCSimulationSystem:
    BASE_INCOME_PER_DAY = 900
    BRANCH_INCOME_PER_DAY = 300
    EXPANSION_COST = 75000
    PORTFOLIO_PURCHASE_COST = 120000
    PORTFOLIO_BOOK_VALUE = 150000
    STANDARD_LOAN_PRINCIPAL = 500000

    @staticmethod
    def starter_companies() -> list[Company]:
        companies: list[Company] = []
        prefixes = (
            "Apex",
            "Harbour",
            "Summit",
            "Keystone",
            "Crown",
            "Pioneer",
            "Atlas",
            "Vector",
            "Meridian",
            "Sterling",
        )
        suffixes = ("Estates", "Properties", "Land", "Homes", "Developments", "Portfolio")
        trait_cycle = (
            NPCCompanyTrait.EXPANSIONIST,
            NPCCompanyTrait.CONSERVATIVE,
            NPCCompanyTrait.EFFICIENCY_FOCUSED,
            NPCCompanyTrait.ASSET_COLLECTOR,
        )

        for index in range(160):
            prefix = prefixes[index % len(prefixes)]
            suffix = suffixes[(index // len(prefixes)) % len(suffixes)]
            company = Company(
                name=f"{prefix} {index + 1} {suffix}",
                company_id=f"npc_property_small_{index + 1}",
                cash=90000 + ((index % 9) * 35000),
                reputation=38.0 + (index % 24),
                npc_traits=(trait_cycle[index % len(trait_cycle)],),
                industry_id="real_estate",
            )
            if index % 4 == 0:
                company.add_division(
                    Division(
                        name="Property Operations",
                        division_id=f"{company.company_id}_operations",
                        branches=[
                            Branch(
                                name=f"{company.name} Office",
                                branch_id=f"{company.company_id}_branch_1",
                                city_id=None,
                            )
                        ],
                    )
                )
            if index % 7 == 0:
                company.add_asset(
                    Asset(
                        name=f"{company.name} Local Portfolio",
                        asset_id=f"{company.company_id}_local_portfolio",
                        value=5_000_000 + ((index % 9) * 4_000_000),
                    )
                )
            companies.append(company)

        for index in range(30):
            portfolio_value = 80_000_000 + (index * 15_000_000)
            company = Company(
                name=f"Continental Property Platform {index + 1}",
                company_id=f"npc_property_mid_{index + 1}",
                cash=4_000_000 + (index * 250_000),
                reputation=56.0 + (index % 18),
                npc_traits=(
                    NPCCompanyTrait.ASSET_COLLECTOR,
                    NPCCompanyTrait.EFFICIENCY_FOCUSED,
                ),
                industry_id="real_estate",
            )
            company.add_asset(
                Asset(
                    name=f"{company.name} Starter Portfolio",
                    asset_id=f"{company.company_id}_portfolio_base",
                    value=portfolio_value,
                )
            )
            companies.append(company)

        for index in range(8):
            portfolio_value = 1_200_000_000 + (index * 650_000_000)
            company = Company(
                name=f"Global Property Trust {index + 1}",
                company_id=f"npc_property_large_{index + 1}",
                cash=90_000_000 + (index * 18_000_000),
                reputation=72.0 + index,
                npc_traits=(NPCCompanyTrait.ASSET_COLLECTOR, NPCCompanyTrait.EXPANSIONIST),
                industry_id="real_estate",
            )
            company.add_asset(
                Asset(
                    name=f"{company.name} Flagship Portfolio",
                    asset_id=f"{company.company_id}_flagship",
                    value=portfolio_value,
                )
            )
            companies.append(company)

        for index in range(4):
            portfolio_value = 12_000_000_000 + (index * 8_000_000_000)
            company = Company(
                name=f"Institutional Property Empire {index + 1}",
                company_id=f"npc_property_mega_{index + 1}",
                cash=750_000_000 + (index * 150_000_000),
                reputation=84.0 + index,
                npc_traits=(
                    NPCCompanyTrait.ASSET_COLLECTOR,
                    NPCCompanyTrait.ACQUISITION_FOCUSED,
                    NPCCompanyTrait.EFFICIENCY_FOCUSED,
                ),
                industry_id="real_estate",
            )
            company.add_asset(
                Asset(
                    name=f"{company.name} Institutional Portfolio",
                    asset_id=f"{company.company_id}_institutional",
                    value=portfolio_value,
                )
            )
            companies.append(company)

        return companies

    def process_days(
        self,
        companies: list[Company],
        days: int,
        world: WorldSystem | None = None,
    ) -> NPCSimulationReport:
        if days <= 0:
            raise ValueError("NPC simulation days must be greater than zero.")

        income_earned = 0
        branches_opened = 0
        assets_collected = 0
        loans_taken = 0
        executives_hired = 0

        for company in companies:
            income_earned += self._earn_money(company=company, days=days)
            loans_taken += self._maybe_take_loan(company)
            executives_hired += self._maybe_hire_executive(company)
            branches_opened += self._maybe_expand(company=company, world=world)
            assets_collected += self._maybe_collect_portfolio(company)
            self._maybe_improve_efficiency(company)

        return NPCSimulationReport(
            income_earned=income_earned,
            branches_opened=branches_opened,
            assets_collected=assets_collected,
            loans_taken=loans_taken,
            executives_hired=executives_hired,
        )

    def _earn_money(self, company: Company, days: int) -> int:
        reputation_factor = 0.75 + (company.reputation / 100)
        branch_income = company.branch_count * self.BRANCH_INCOME_PER_DAY
        asset_income = round(sum(asset.value for asset in company.assets) * 0.00018)
        daily_income = round((self.BASE_INCOME_PER_DAY + branch_income + asset_income) * reputation_factor)
        if company.has_npc_trait(NPCCompanyTrait.EFFICIENCY_FOCUSED):
            daily_income = round(daily_income * 1.15)
        if company.has_npc_trait(NPCCompanyTrait.CONSERVATIVE):
            daily_income = round(daily_income * 0.9)

        income = daily_income * days
        company.add_cash(income)
        return income

    def _maybe_take_loan(self, company: Company) -> int:
        wants_capital = company.has_npc_trait(NPCCompanyTrait.EXPANSIONIST) or company.has_npc_trait(
            NPCCompanyTrait.ASSET_COLLECTOR
        )
        if not wants_capital:
            return 0
        if company.cash >= self.EXPANSION_COST * 2:
            return 0
        if company.total_debt >= self.STANDARD_LOAN_PRINCIPAL:
            return 0

        company.take_loan(principal=self.STANDARD_LOAN_PRINCIPAL, term_months=60)
        return 1

    def _maybe_hire_executive(self, company: Company) -> int:
        if company.executives:
            return 0
        if company.cash < 180000:
            return 0

        executive = Executive(
            name=f"{company.name} Operator",
            title="Property Director",
            salary=145000,
            loyalty=58.0,
            reputation=55.0,
            skills=SkillRatings(leadership=62.0, finance=60.0, operations=64.0),
        )
        company.spend_cash(75000)
        company.add_executive(executive)
        return 1

    def _maybe_expand(self, company: Company, world: WorldSystem | None = None) -> int:
        if company.has_npc_trait(NPCCompanyTrait.CONSERVATIVE) and company.cash < 600000:
            return 0
        if not company.has_npc_trait(NPCCompanyTrait.EXPANSIONIST):
            return 0
        if company.cash < self.EXPANSION_COST:
            return 0

        company.spend_cash(self.EXPANSION_COST)
        division = self._ensure_operations_division(company)
        branch_number = company.branch_count + 1
        city_id = self._target_city_id(world=world, branch_number=branch_number)
        division.add_branch(
            Branch(
                name=f"{company.name} Office {branch_number}",
                branch_id=f"{company.company_id}_office_{branch_number}",
                city_id=city_id,
            )
        )
        return 1

    def _maybe_collect_portfolio(self, company: Company) -> int:
        if not company.has_npc_trait(NPCCompanyTrait.ASSET_COLLECTOR):
            return 0
        if company.cash < self.PORTFOLIO_PURCHASE_COST:
            return 0

        company.spend_cash(self.PORTFOLIO_PURCHASE_COST)
        asset_number = len(company.assets) + 1
        company.add_asset(
            Asset(
                name=f"{company.name} Portfolio {asset_number}",
                asset_id=f"{company.company_id}_portfolio_{asset_number}",
                value=self.PORTFOLIO_BOOK_VALUE,
            )
        )
        return 1

    def _maybe_improve_efficiency(self, company: Company) -> None:
        if not company.has_npc_trait(NPCCompanyTrait.EFFICIENCY_FOCUSED):
            return

        company.set_reputation(min(100.0, company.reputation + 0.1))

    def _ensure_operations_division(self, company: Company) -> Division:
        division_id = f"{company.company_id}_operations"
        division = company.get_division(division_id)
        if division is None:
            division = Division(name="Property Operations", division_id=division_id)
            company.add_division(division)

        return division

    def _target_city_id(self, world: WorldSystem | None, branch_number: int) -> str | None:
        if world is None or not world.cities:
            return None

        cities = sorted(world.cities, key=lambda city: city.demand_score, reverse=True)
        return cities[(branch_number - 1) % len(cities)].city_id
