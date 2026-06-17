# tests/test_vertical_slice.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from core.clock import GameSpeed
from core.engine import GameEngine
from core.save_manager import SaveManager
from core.state import GameState
from gameplay.service import GameplayService
from news.models import NewsCategory, NewsFeed


def test_news_feed_stores_headline_items() -> None:
    state = GameState(world_id="news", world_name="News")

    item = state.news_feed.add(
        "Platinum Properties Purchases New York Office",
        NewsCategory.REAL_ESTATE,
        state.clock.current_date,
    )

    loaded = NewsFeed.from_dict(state.news_feed.to_dict())

    assert item.headline == "Platinum Properties Purchases New York Office"
    assert loaded.recent(1)[0].category is NewsCategory.REAL_ESTATE


def test_new_game_sets_hq_and_property_company_name() -> None:
    service = GameplayService()

    state = service.new_game(
        company_name="Northstar Estates",
        starting_industry="real_estate",
        hq_city_id="new_york_city",
    )

    company = state.player.holding_company.companies[0]

    assert state.metadata["game_started"] is True
    assert state.metadata["starting_industry"] == "real_estate"
    assert state.metadata["hq_city_name"] == "New York City"
    assert company.name == "Northstar Estates"
    assert company.industry_id == "real_estate"
    assert company.branch_count == 1
    assert len(company.executives) == 1


def test_new_game_rejects_removed_industries() -> None:
    service = GameplayService()

    try:
        service.new_game("Old Bank", starting_industry="banking", hq_city_id="new_york_city")
    except ValueError as exc:
        assert "Real Estate only" in str(exc)
    else:
        raise AssertionError("Expected non-property industries to be unavailable.")


def test_property_purchase_preview_explains_cost_income_and_yield() -> None:
    state = GameState(world_id="preview", world_name="Preview")
    service = GameplayService()

    estimate = service.estimate_property_purchase(
        state,
        city_id="new_york_city",
        building_type_id="small_office",
    )

    assert estimate["cost"] > 0
    assert estimate["rent"] > estimate["maintenance"]
    assert estimate["yield"] > 0
    assert estimate["occupancy"] > 0


def test_property_purchase_uses_available_group_cash() -> None:
    service = GameplayService()
    state = service.new_game(
        company_name="Platinum Estates",
        starting_industry="real_estate",
        hq_city_id="new_york_city",
    )
    company = state.player.holding_company.companies[0]
    listing = min(service.property_listings(state, "new_york_city"), key=lambda deal: deal.asking_price)
    quote = service.quote_property_purchase(state, listing.listing_id)
    state.player.holding_company.cash = quote.cash_required - 50000
    company.cash = 100000

    service.buy_property_listing(state, listing.listing_id)

    assert len(state.player_properties) == 1
    assert state.player.holding_company.total_cash() == 50000


def test_property_purchase_generates_income_over_time() -> None:
    state = GameState(world_id="property", world_name="Property")
    service = GameplayService()

    property_ = service.buy_property(state, city_id="new_york_city", building_type_id="small_office")
    starting_cash = state.player.holding_company.cash
    result = service.process_player_days(state, days=31)

    assert property_.city_id == "new_york_city"
    assert result.revenue > result.expenses
    assert state.player.holding_company.cash > starting_cash
    assert state.financials.income_statement.total_revenue > 0


def test_operating_history_records_graph_metrics() -> None:
    state = GameState(world_id="history", world_name="History")
    service = GameplayService()

    service.buy_property(state, city_id="new_york_city", building_type_id="small_office")
    service.process_player_days(state, days=31)

    history = state.metadata["operating_history"]

    assert len(history) == 1
    assert history[0]["revenue"] > 0
    assert history[0]["profit"] > 0
    assert history[0]["company_value"] > 0


def test_company_loan_quote_draw_and_repayment_are_visible() -> None:
    state = GameState(world_id="loans", world_name="Loans")
    service = GameplayService()
    company = service.ensure_starting_company(state)

    quote = service.estimate_company_loan(state, principal=250000, term_months=48)
    service.take_company_loan(state, principal=250000)
    loan = company.loans[0]
    service.repay_company_loan(state, loan.loan_id, 100000)

    assert quote["principal"] == 250000
    assert company.total_debt == 150000
    assert state.financials.cash_flow.financing["property_loan_draw"] == 250000
    assert state.financials.cash_flow.financing["property_loan_repayment"] == -100000


def test_financial_statement_lines_show_income_balance_and_cash_flow() -> None:
    state = GameState(world_id="statements", world_name="Statements")
    service = GameplayService()

    service.ensure_starting_company(state)
    service.buy_property(state)
    service.take_company_loan(state, principal=200000)
    service.process_player_days(state, days=31)

    income_sections = {section for section, _, _ in service.income_statement_lines(state)}
    balance_lines = {(section, line) for section, line, _ in service.balance_sheet_lines(state)}
    cash_flow_sections = {section for section, _, _ in service.cash_flow_lines(state)}

    assert {"Revenue", "Expense", "Profit"}.issubset(income_sections)
    assert ("Assets", "holding_cash") in balance_lines
    assert ("Liabilities", "property_debt") in balance_lines
    assert {"Operating", "Investing", "Financing", "Net"}.issubset(cash_flow_sections)


def test_vertical_slice_save_loads_properties_financials_and_news() -> None:
    with TemporaryDirectory() as directory:
        state = GameState(world_id="vertical", world_name="Vertical")
        service = GameplayService()
        service.ensure_starting_company(state)
        service.buy_property(state)
        service.take_company_loan(state)
        service.process_player_days(state, days=31)
        manager = SaveManager(save_root=Path(directory))

        manager.save_world(state, slot_name="slice")
        loaded = manager.load_world("vertical", slot_name="slice")

    assert loaded.player.holding_company.get_company("platinum_properties") is not None
    assert len(loaded.player_properties) == 1
    assert loaded.financials.income_statement.total_revenue > 0
    assert loaded.news_feed.recent(1)


def test_engine_tick_processes_player_and_competitors() -> None:
    state = GameState(world_id="engine-slice", world_name="Engine Slice")
    engine = GameEngine(state=state)
    engine.gameplay.ensure_starting_company(state)
    engine.gameplay.buy_property(state)

    engine.set_speed(GameSpeed.ONE_X)
    snapshot = engine.tick()
    for _ in range(30):
        snapshot = engine.tick()

    assert snapshot.tick_count == 31
    assert state.metadata["last_revenue"] > 0
    assert state.news_feed.recent(1)
    assert state.npc_companies
