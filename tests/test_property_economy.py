# tests/test_property_economy.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from datetime import date

from core.state import GameState
from gameplay.service import GameplayService


def _unlock_city_managers(state: GameState) -> None:
    state.metadata["completed_research"] = [
        "tenant_screening",
        "preventive_maintenance",
        "centralised_leasing",
        "predictive_maintenance",
        "property_management_division",
    ]


def test_deal_generation_creates_full_city_market() -> None:
    state = GameState(world_id="deals", world_name="Deals")
    service = GameplayService()

    listings = service.property_listings(state, "new_york_city")

    assert 50 <= len(listings) <= 70
    assert any(listing.size_sqm < 1000 for listing in listings)
    assert any(listing.size_sqm > 10000 for listing in listings)
    assert all(listing.monthly_revenue > listing.monthly_expenses for listing in listings)
    assert all(listing.days_remaining > 0 for listing in listings)


def test_deal_filtering_and_sorting_by_price_yield_and_zoning() -> None:
    state = GameState(world_id="filters", world_name="Filters")
    service = GameplayService()

    office_deals = service.filter_property_deals(
        state,
        city_id="new_york_city",
        zoning="Office",
        min_yield=0.04,
        sort_key="price_low",
    )
    expensive_first = service.filter_property_deals(state, city_id="new_york_city", sort_key="price_high")

    assert office_deals
    assert all(deal.zoning.value == "Office" for deal in office_deals)
    assert office_deals == sorted(office_deals, key=lambda deal: deal.asking_price)
    assert expensive_first[0].asking_price >= expensive_first[-1].asking_price


def test_cash_purchase_affordability_includes_stamp_duty() -> None:
    state = GameState(world_id="cash", world_name="Cash")
    service = GameplayService()
    service.ensure_starting_company(state)
    listing = min(service.property_listings(state, "new_york_city"), key=lambda deal: deal.asking_price)
    quote = service.quote_property_purchase(state, listing.listing_id)

    state.player.holding_company.cash = quote.cash_required - 1
    for company in state.player.holding_company.companies:
        company.cash = 0

    try:
        service.buy_property_listing(state, listing.listing_id)
    except ValueError as exc:
        assert "Not enough cash" in str(exc)
    else:
        raise AssertionError("Expected purchase to fail when fees push it over available cash.")

    state.player.holding_company.cash = quote.cash_required
    for company in state.player.holding_company.companies:
        company.cash = 0

    service.buy_property_listing(state, listing.listing_id)

    assert len(state.player_properties) == 1
    assert state.player.holding_company.total_cash() == 0


def test_finance_purchase_approval_and_rejection_explain_limits() -> None:
    state = GameState(world_id="finance-purchase", world_name="Finance Purchase")
    service = GameplayService()
    service.ensure_starting_company(state)
    affordable = min(service.property_listings(state, "detroit"), key=lambda deal: deal.asking_price)
    expensive = max(service.property_listings(state, "new_york_city"), key=lambda deal: deal.asking_price)

    approved = service.quote_property_purchase(state, affordable.listing_id, deposit_percent=0.35)
    state.player.holding_company.cash = 500000
    for company in state.player.holding_company.companies:
        company.cash = 0
    rejected = service.quote_property_purchase(state, expensive.listing_id, deposit_percent=0.2)

    assert approved.approval.approved
    assert approved.loan_amount > 0
    assert not rejected.approval.approved
    assert rejected.approval.reasons


def test_loan_borrowing_limits_prevent_infinite_debt() -> None:
    state = GameState(world_id="loan-limits", world_name="Loan Limits")
    service = GameplayService()
    service.ensure_starting_company(state)

    reasonable = service.estimate_company_loan(state, principal=250000, term_months=60)
    extreme = service.estimate_company_loan(state, principal=250000000, term_months=60)

    assert reasonable["approved"] is True
    assert extreme["approved"] is False
    assert int(extreme["max_loan_amount"]) < 250000000


def test_loan_capacity_scales_with_cash_and_portfolio_value() -> None:
    service = GameplayService()
    cash_state = GameState(world_id="cash-loan-scale", world_name="Cash Loan Scale")
    service.ensure_starting_company(cash_state)
    cash_state.player.holding_company.cash = 50_000_000
    for company in cash_state.player.holding_company.companies:
        company.cash = 0

    cash_quote = service.estimate_company_loan(cash_state, principal=25_000_000, term_months=120)

    portfolio_state = GameState(world_id="portfolio-loan-scale", world_name="Portfolio Loan Scale")
    service.ensure_starting_company(portfolio_state)
    portfolio_state.player.holding_company.cash = 500_000_000
    target = next(
        opportunity
        for opportunity in service.portfolio_acquisition_opportunities(portfolio_state)
        if opportunity.portfolio_value >= 100_000_000
    )
    service.buy_competitor_portfolio(portfolio_state, target.company_id)
    portfolio_state.player.holding_company.cash = 2_000_000
    for company in portfolio_state.player.holding_company.companies:
        company.cash = 0

    portfolio_quote = service.estimate_company_loan(portfolio_state, principal=50_000_000, term_months=120)

    assert cash_quote["approved"] is True
    assert int(cash_quote["max_loan_amount"]) >= 25_000_000
    assert portfolio_quote["approved"] is True
    assert int(portfolio_quote["max_loan_amount"]) >= 50_000_000


def test_monthly_rent_collection_and_loan_repayment() -> None:
    state = GameState(world_id="monthly", world_name="Monthly")
    service = GameplayService()
    service.ensure_starting_company(state)
    service.buy_property(state)
    loan = service.take_company_loan(state, principal=250000, term_months=48)
    starting_debt = loan.principal

    result = service.process_player_days(state, days=31)

    assert result.revenue > 0
    assert state.financials.income_statement.revenue["property_rent"] > 0
    assert loan.principal < starting_debt
    assert state.financials.cash_flow.financing["scheduled_loan_principal"] < 0


def test_tax_summary_tracks_property_tax_and_taxable_profit() -> None:
    state = GameState(world_id="tax", world_name="Tax")
    service = GameplayService()
    service.ensure_starting_company(state)
    service.buy_property(state)

    service.process_player_days(state, days=31)
    tax = service.tax_summary(state)

    assert tax["gross_revenue"] > 0
    assert tax["property_tax"] > 0
    assert "corporate_tax" in tax
    assert "capital_gains_tax_rate" in tax


def test_tax_detail_exposes_rates_forecast_and_history() -> None:
    state = GameState(world_id="tax-detail", world_name="Tax Detail")
    service = GameplayService()
    service.ensure_starting_company(state)
    service.buy_property(state)

    service.process_player_days(state, days=31)
    detail = service.tax_detail(state)

    assert {"summary", "rates", "forecast", "monthly_history"}.issubset(detail)
    assert len(detail["summary"]) >= 8
    assert len(detail["rates"]) >= 5
    assert len(detail["forecast"]) >= 5
    assert detail["monthly_history"]


def test_debug_cash_grant_adds_money_and_alert() -> None:
    state = GameState(world_id="debug-cash", world_name="Debug Cash")
    service = GameplayService()
    service.ensure_starting_company(state)
    before = state.player.holding_company.total_cash()

    service.grant_debug_cash(state, 1000000)

    assert state.player.holding_company.total_cash() == before + 1000000
    assert service.alerts(state)[0]["title"] == "Developer cash grant"


def test_credit_rating_factors_include_active_and_inactive_impacts() -> None:
    state = GameState(world_id="credit-factors", world_name="Credit Factors")
    service = GameplayService()
    service.ensure_starting_company(state)

    factors = service.credit_rating_factors(state)
    impacts = {str(factor["factor"]): int(factor["impact"]) for factor in factors}
    statuses = {str(factor["factor"]): str(factor["status"]) for factor in factors}

    assert impacts["Base company profile"] == 500
    assert "Credit packaging research" in impacts
    assert impacts["Credit packaging research"] == 0
    assert statuses["Credit packaging research"] == "Inactive"
    assert sum(impacts.values()) == service.credit_rating(state).score


def test_portfolio_groups_properties_by_city() -> None:
    state = GameState(world_id="portfolio", world_name="Portfolio")
    service = GameplayService()
    service.ensure_starting_company(state)

    new_york_deal = min(service.property_listings(state, "new_york_city"), key=lambda deal: deal.asking_price)
    los_angeles_deal = min(service.property_listings(state, "los_angeles"), key=lambda deal: deal.asking_price)
    service.buy_property_listing(state, new_york_deal.listing_id)
    service.buy_property_listing(state, los_angeles_deal.listing_id)

    rows = service.portfolio_by_city(state)
    cities = {str(row["city"]) for row in rows}

    assert {"New York City", "Los Angeles"}.issubset(cities)
    assert all(int(row["portfolio_value"]) > 0 for row in rows)


def test_construction_progresses_daily_and_creates_property() -> None:
    state = GameState(world_id="construction", world_name="Construction")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 20000000
    for company in state.player.holding_company.companies:
        company.cash = 0
    land = min(service.land_listings(state, "new_york_city"), key=lambda listing: listing.asking_price)
    parcel = service.buy_land_listing(state, land.listing_id)
    option = service.development_options(parcel.zoning)[0]
    project = service.start_development(state, parcel.parcel_id, option.option_id, "budgetbuild")

    service.process_player_days(state, days=project.total_days)

    assert project not in state.development_projects
    assert parcel.developed is True
    assert any(property_.city_id == parcel.city_id for property_ in state.player_properties)


def test_monthly_report_and_history_store_visual_metrics() -> None:
    state = GameState(world_id="reports", world_name="Reports")
    service = GameplayService()
    service.ensure_starting_company(state)
    service.buy_property(state)

    service.process_player_days(state, days=31)
    reports = service.pop_pending_reports(state)
    history = state.metadata["operating_history"][0]

    assert reports[0]["type"] == "monthly"
    assert reports[0]["income"]["Residential rent"] + reports[0]["income"]["Office rent"] + reports[0]["income"]["Commercial rent"] + reports[0]["income"]["Industrial rent"] > 0
    assert "Loan repayments" in reports[0]["expenses"]
    assert history["cash"] >= 0
    assert "debt" in history
    assert "credit_rating" in history
    assert "occupancy" in history
    assert "tax_paid" in history


def test_quarterly_report_summarises_property_performance() -> None:
    state = GameState(world_id="quarterly", world_name="Quarterly")
    service = GameplayService()
    service.ensure_starting_company(state)
    service.buy_property(state)

    service.process_player_days(state, days=90)
    reports = service.pop_pending_reports(state)
    quarterly = [report for report in reports if report["type"] == "quarterly"]

    assert quarterly
    summary = quarterly[-1]["summary"]
    assert summary["Revenue"] > 0
    assert "Best city" in summary
    assert "Credit rating change" in summary


def test_research_tree_unlocks_bonuses_and_credit_support() -> None:
    state = GameState(world_id="research", world_name="Research")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 1000000
    before = service.credit_rating(state).score

    service.start_research(state, "lender_relations")
    service.start_research(state, "credit_packaging")

    tree = service.research_tree(state)
    assert any(node["node_id"] == "credit_packaging" and node["status"] == "Completed" for node in tree)
    assert service.credit_rating(state).score > before
    assert service.alerts(state)[0]["title"] == "Research complete"


def test_planning_permission_depends_on_project_size_and_research() -> None:
    state = GameState(world_id="planning", world_name="Planning")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 50000000
    for company in state.player.holding_company.companies:
        company.cash = 0
        company.reputation = 5.0
    land = max(service.land_listings(state, "detroit"), key=lambda listing: listing.size_sqm)
    parcel = service.buy_land_listing(state, land.listing_id)
    option = service.development_options(parcel.zoning)[-1]

    before = service.planning_assessment(state, parcel.parcel_id, option.option_id)
    service.start_research(state, "zoning_liaison")
    service.start_research(state, "large_project_permits")
    after = service.planning_assessment(state, parcel.parcel_id, option.option_id)

    assert before["required"] is True
    assert after["score"] > before["score"]


def test_negotiation_records_counter_accept_reject_and_withdraw() -> None:
    state = GameState(world_id="negotiation", world_name="Negotiation")
    service = GameplayService()
    service.ensure_starting_company(state)
    listing = min(service.property_listings(state, "phoenix"), key=lambda deal: deal.asking_price)

    rejected = service.negotiate_property_offer(state, listing.listing_id, round(listing.asking_price * 0.75))
    countered = service.negotiate_property_offer(state, listing.listing_id, round(listing.asking_price * 0.9))
    accepted = service.negotiate_property_offer(state, listing.listing_id, round(listing.asking_price * 0.98))
    service.withdraw_negotiation(state, accepted.negotiation_id)

    assert rejected.status == "Rejected"
    assert countered.status == "Countered"
    assert accepted.status == "Accepted"
    assert state.metadata["negotiations"][accepted.negotiation_id]["status"] == "Withdrawn"


def test_negotiation_accepts_counteroffer_and_better_follow_up_offer() -> None:
    state = GameState(world_id="counter-negotiation", world_name="Counter Negotiation")
    service = GameplayService()
    service.ensure_starting_company(state)
    listings = sorted(service.property_listings(state, "phoenix"), key=lambda deal: deal.asking_price)

    countered = service.negotiate_property_offer(state, listings[0].listing_id, round(listings[0].asking_price * 0.9))
    assert countered.status == "Countered"
    assert countered.counteroffer is not None

    accepted_counter = service.accept_counteroffer(state, countered.negotiation_id)
    assert accepted_counter.status == "Accepted"
    assert accepted_counter.player_offer == countered.counteroffer

    second_counter = service.negotiate_property_offer(state, listings[1].listing_id, round(listings[1].asking_price * 0.9))
    assert second_counter.counteroffer is not None
    better_offer = service.negotiate_property_offer(state, listings[1].listing_id, int(second_counter.counteroffer) + 50000)

    assert better_offer.status == "Accepted"
    assert better_offer.counteroffer is None


def test_competitor_portfolio_acquisition_buys_whole_portfolio() -> None:
    state = GameState(world_id="acquisition", world_name="Acquisition")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 50000000
    opportunities = service.portfolio_acquisition_opportunities(state)
    target = opportunities[0]

    service.buy_competitor_portfolio(state, target.company_id)

    assert len(state.player_properties) >= target.property_count
    assert not next(company for company in state.npc_companies if company.company_id == target.company_id).assets
    assert service.alerts(state)[0]["title"] == "Portfolio acquired"


def test_portfolio_acquisition_market_has_large_and_institutional_targets() -> None:
    state = GameState(world_id="acquisition-range", world_name="Acquisition Range")
    service = GameplayService()

    opportunities = service.portfolio_acquisition_opportunities(state)
    values = [opportunity.portfolio_value for opportunity in opportunities]

    assert any(100_000_000 <= value < 1_000_000_000 for value in values)
    assert any(1_000_000_000 <= value < 10_000_000_000 for value in values)
    assert any(value >= 10_000_000_000 for value in values)
    assert max(opportunity.property_count for opportunity in opportunities) > 100


def test_company_value_excludes_idle_cash() -> None:
    state = GameState(world_id="value-cash", world_name="Value Cash")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 2_000_000_000
    for company in state.player.holding_company.companies:
        company.cash = 500_000_000

    assert service.company_value(state) == 0

    service.buy_property(state)

    assert 0 < service.company_value(state) < state.player.holding_company.total_cash()


def test_research_tree_has_long_endgame_branches() -> None:
    state = GameState(world_id="research-depth", world_name="Research Depth")
    service = GameplayService()

    tree = service.research_tree(state)
    costs = [int(node["cost"]) for node in tree]
    node_ids = {str(node["node_id"]) for node in tree}

    assert len(tree) >= 30
    assert max(costs) >= 5_000_000_000
    assert "property_empire_platform" in node_ids


def test_all_research_nodes_have_exact_numeric_effects() -> None:
    state = GameState(world_id="research-effects", world_name="Research Effects")
    service = GameplayService()

    tree = service.research_tree(state)
    effect_rows = service.research_effect_rows(state)
    manager_node = next(node for node in tree if node["node_id"] == "property_management_division")

    assert all(node["effects"] for node in tree)
    assert all("%" in node["effect_summary"] or "+" in node["effect_summary"] or "Unlocks" in node["effect_summary"] for node in tree)
    assert manager_node["effect_summary"] == "Unlocks City Managers; +10.0% city manager monthly budget efficiency"
    assert len(effect_rows) >= len(tree)


def test_research_tree_exposes_available_starting_unlocks() -> None:
    state = GameState(world_id="research-ui", world_name="Research UI")
    service = GameplayService()

    tree = service.research_tree(state)
    statuses = {str(node["node_id"]): str(node["status"]) for node in tree}

    assert statuses["tenant_screening"] == "Available"
    assert statuses["rent_analytics"] == "Locked"

    service.start_research(state, "tenant_screening")
    refreshed = service.research_tree(state)
    refreshed_statuses = {str(node["node_id"]): str(node["status"]) for node in refreshed}

    assert refreshed_statuses["tenant_screening"] == "Completed"
    assert refreshed_statuses["rent_analytics"] == "Available"


def test_city_managers_are_locked_until_researched() -> None:
    state = GameState(world_id="manager-lock", world_name="Manager Lock")
    service = GameplayService()
    service.ensure_starting_company(state)
    service.buy_property_listing(
        state,
        min(service.property_listings(state, "detroit"), key=lambda deal: deal.asking_price).listing_id,
    )

    try:
        service.assign_city_manager(
            state,
            city_id="detroit",
            name="Detroit Asset Desk",
            monthly_budget=5_000_000,
            min_yield=0.04,
            max_property_price=3_000_000,
            allowed_property_types=("Residential",),
            aggressiveness="Balanced",
            cash_reserve_requirement=1_000_000,
        )
    except ValueError as exc:
        assert "Property Management Division" in str(exc)
    else:
        raise AssertionError("Expected city managers to remain locked before research.")

    _unlock_city_managers(state)
    manager = service.assign_city_manager(
        state,
        city_id="detroit",
        name="Detroit Asset Desk",
        monthly_budget=5_000_000,
        min_yield=0.04,
        max_property_price=3_000_000,
        allowed_property_types=("Residential",),
        aggressiveness="Balanced",
        cash_reserve_requirement=1_000_000,
    )

    assert manager.city_id == "detroit"
    assert service.city_manager_rows(state)[0]["status"] == "Active"


def test_city_manager_purchases_only_within_rules() -> None:
    state = GameState(world_id="manager-buy", world_name="Manager Buy")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 50_000_000
    for company in state.player.holding_company.companies:
        company.cash = 0
    service.buy_property_listing(
        state,
        min(service.property_listings(state, "detroit"), key=lambda deal: deal.asking_price).listing_id,
    )
    _unlock_city_managers(state)

    service.assign_city_manager(
        state,
        city_id="detroit",
        name="Detroit Residential Desk",
        monthly_budget=5_000_000,
        min_yield=0.04,
        max_property_price=3_000_000,
        allowed_property_types=("Residential",),
        aggressiveness="Balanced",
        cash_reserve_requirement=1_000_000,
    )
    before = len(state.player_properties)

    service.process_player_days(state, days=31)
    rows = service.city_manager_rows(state)
    purchased = state.player_properties[before:]

    assert rows[0]["properties_purchased"] >= 1
    assert purchased
    assert all(property_.zoning == "Residential" for property_ in purchased)
    assert all((property_.purchase_price or 0) <= 3_000_000 for property_ in purchased)


def test_city_manager_enforces_minimum_yield_and_budget() -> None:
    state = GameState(world_id="manager-limits", world_name="Manager Limits")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 50_000_000
    for company in state.player.holding_company.companies:
        company.cash = 0
    service.buy_property_listing(
        state,
        min(service.property_listings(state, "detroit"), key=lambda deal: deal.asking_price).listing_id,
    )
    _unlock_city_managers(state)

    service.assign_city_manager(
        state,
        city_id="detroit",
        name="Detroit Risk Desk",
        monthly_budget=250_000,
        min_yield=0.2,
        max_property_price=10_000_000,
        allowed_property_types=("Residential", "Office", "Commercial", "Industrial"),
        aggressiveness="Aggressive",
        cash_reserve_requirement=1_000_000,
    )

    service.process_player_days(state, days=31)
    row = service.city_manager_rows(state)[0]

    assert row["properties_purchased"] == 0
    assert row["capital_invested"] == 0


def test_vacancy_fluctuates_actual_occupancy_and_affects_value() -> None:
    state = GameState(world_id="vacancy", world_name="Vacancy")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 3_000_000_000
    for company in state.player.holding_company.companies:
        company.cash = 0
    listing = max(service.property_listings(state, "new_york_city"), key=lambda deal: deal.size_sqm)
    property_ = service.buy_property_listing(state, listing.listing_id)
    city = state.world.get_city("new_york_city")
    assert city is not None
    property_.expected_occupancy = 0.95
    property_.tenants.clear()
    initial_value = property_.property_value(city)

    service.process_player_days(state, days=31)

    assert property_.expected_occupancy == 0.95
    assert property_.occupancy.rate > 0
    assert property_.property_value(city) != initial_value


def test_vacancy_events_store_temporary_city_modifiers() -> None:
    state = GameState(world_id="vacancy-events", world_name="Vacancy Events")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.metadata["vacancy_events"] = {"new_york_city:Office": {"months": 2, "impact": -0.12}}

    service.process_player_days(state, days=31)

    assert state.metadata["vacancy_events"]["new_york_city:Office"]["months"] == 1
    assert state.metadata["vacancy_modifiers"]["new_york_city:Office"] == -0.12


def test_mega_project_eligibility_and_cost_range() -> None:
    state = GameState(world_id="mega", world_name="Mega")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 100_000_000_000
    target = next(
        opportunity
        for opportunity in service.portfolio_acquisition_opportunities(state)
        if opportunity.portfolio_value >= 10_000_000_000
    )
    service.buy_competitor_portfolio(state, target.company_id)

    project = service.maybe_generate_mega_project(state, current_date=date(2032, 1, 1), force=True)

    assert service.mega_project_eligible(state)
    assert project is not None
    assert 1_000_000_000 <= project.estimated_cost <= 40_000_000_000
    assert 365 <= project.construction_days <= 365 * 7
    assert service.mega_project_rows(state)


def test_mega_project_frequency_limits_regular_generation() -> None:
    state = GameState(world_id="mega-frequency", world_name="Mega Frequency")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 100_000_000_000
    target = next(
        opportunity
        for opportunity in service.portfolio_acquisition_opportunities(state)
        if opportunity.portfolio_value >= 10_000_000_000
    )
    service.buy_competitor_portfolio(state, target.company_id)

    first = service.maybe_generate_mega_project(state, current_date=date(2030, 1, 1), force=True)
    assert first is not None
    service.reject_mega_project(state, first.project_id)
    blocked = service.maybe_generate_mega_project(state, current_date=date(2031, 1, 1))

    assert blocked is None


def test_mega_project_proceed_reserves_capital_and_tracks_project() -> None:
    state = GameState(world_id="mega-proceed", world_name="Mega Proceed")
    service = GameplayService()
    service.ensure_starting_company(state)
    state.player.holding_company.cash = 100_000_000_000
    target = next(
        opportunity
        for opportunity in service.portfolio_acquisition_opportunities(state)
        if opportunity.portfolio_value >= 10_000_000_000
    )
    service.buy_competitor_portfolio(state, target.company_id)
    project = service.maybe_generate_mega_project(state, current_date=date(2035, 1, 1), force=True)
    assert project is not None
    before_cash = state.player.holding_company.total_cash()

    proceeding = service.proceed_mega_project(state, project.project_id)

    assert proceeding.status == "Proceeding"
    assert state.player.holding_company.total_cash() == before_cash - round(project.estimated_cost * 0.2)


def test_bad_cashflow_can_bankrupt_property_company() -> None:
    state = GameState(world_id="bankrupt", world_name="Bankrupt")
    service = GameplayService()
    service.ensure_starting_company(state)
    property_ = service.buy_property(state)
    property_.monthly_revenue_override = 100
    property_.monthly_expenses_override = 1000000
    state.player.holding_company.cash = 0
    for company in state.player.holding_company.companies:
        company.cash = 0

    service.process_player_days(state, days=31)

    assert state.metadata["bankrupt"] is True
    assert any(alert["title"] == "Bankruptcy warning" for alert in service.alerts(state))
