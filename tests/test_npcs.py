# tests/test_npcs.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from companies.models import Company, NPCCompanyTrait
from core.clock import GameSpeed
from core.engine import GameEngine
from core.save_manager import SaveManager
from core.state import GameState
from npcs.models import NPCSimulationSystem


def test_npc_traits_live_on_real_companies_and_round_trip() -> None:
    company = Company(
        name="Trait Corp",
        company_id="trait_corp",
        cash=500000,
        npc_traits=(NPCCompanyTrait.EXPANSIONIST, NPCCompanyTrait.EFFICIENCY_FOCUSED),
    )

    loaded = Company.from_dict(company.to_dict())

    assert loaded.has_npc_trait(NPCCompanyTrait.EXPANSIONIST)
    assert loaded.has_npc_trait(NPCCompanyTrait.EFFICIENCY_FOCUSED)


def test_npc_companies_are_saved_with_game_state() -> None:
    with TemporaryDirectory() as directory:
        state = GameState(world_id="npc-save", world_name="NPC Save", npc_companies=[])
        state.npc_companies.append(
            Company(
                name="Saved NPC",
                company_id="saved_npc",
                cash=250000,
                npc_traits=(NPCCompanyTrait.CONSERVATIVE,),
            )
        )
        manager = SaveManager(save_root=Path(directory))

        manager.save_world(state, slot_name="npcs")
        loaded = manager.load_world("npc-save", slot_name="npcs")

    assert loaded.npc_companies[0].company_id == "saved_npc"
    assert loaded.npc_companies[0].has_npc_trait(NPCCompanyTrait.CONSERVATIVE)


def test_starter_companies_are_property_focused() -> None:
    companies = NPCSimulationSystem.starter_companies()

    assert len(companies) >= 150
    assert all(company.industry_id == "real_estate" for company in companies)
    assert any(company.assets for company in companies)


def test_npcs_earn_money_on_simulation_tick() -> None:
    company = Company(name="Earner", company_id="earner", cash=100000)
    system = NPCSimulationSystem()

    report = system.process_days(companies=[company], days=5)

    assert report.income_earned > 0
    assert company.cash > 100000


def test_expansionist_npc_takes_loan_and_expands() -> None:
    company = Company(
        name="Expansionist",
        company_id="expansionist",
        cash=1000,
        npc_traits=(NPCCompanyTrait.EXPANSIONIST,),
    )
    system = NPCSimulationSystem()

    report = system.process_days(companies=[company], days=1)

    assert report.loans_taken == 1
    assert report.branches_opened == 1
    assert len(company.loans) == 1
    assert company.branch_count == 1


def test_asset_collector_npc_buys_property_portfolios() -> None:
    company = Company(
        name="Collector",
        company_id="collector",
        cash=250000,
        npc_traits=(NPCCompanyTrait.ASSET_COLLECTOR,),
    )
    system = NPCSimulationSystem()

    report = system.process_days(companies=[company], days=1)

    assert report.assets_collected == 1
    assert company.assets[0].value == NPCSimulationSystem.PORTFOLIO_BOOK_VALUE


def test_efficiency_focused_npc_improves_reputation() -> None:
    company = Company(
        name="Efficient",
        company_id="efficient",
        cash=250000,
        reputation=50.0,
        npc_traits=(NPCCompanyTrait.EFFICIENCY_FOCUSED,),
    )
    system = NPCSimulationSystem()

    system.process_days(companies=[company], days=1)

    assert company.reputation == 50.1


def test_npc_companies_can_take_real_company_loans() -> None:
    company = Company(name="Borrower", company_id="borrower", cash=100000)

    loan = company.take_loan(principal=250000, term_months=48)

    assert company.cash == 350000
    assert company.loans == [loan]
    assert company.total_debt == 250000


def test_engine_tick_processes_npc_companies() -> None:
    company = Company(
        name="Engine NPC",
        company_id="engine_npc",
        cash=250000,
        npc_traits=(NPCCompanyTrait.ASSET_COLLECTOR,),
    )
    state = GameState(world_id="engine-npc", world_name="Engine NPC", npc_companies=[company])
    engine = GameEngine(state=state)

    engine.set_speed(GameSpeed.ONE_X)
    engine.tick()

    assert state.tick_count == 1
    assert state.npc_companies[0].cash > 250000 or state.npc_companies[0].assets
