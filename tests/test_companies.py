# tests/test_companies.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from companies.models import Branch, Company, Division, Executive, HoldingCompany, Player, SkillRatings
from core.save_manager import SaveManager
from core.state import GameState


def test_player_holding_company_owns_property_company() -> None:
    branch = Branch(name="New York HQ", branch_id="branch_new_york", city_id="new_york_city")
    division = Division(name="Property Operations", division_id="division_properties")
    company = Company(name="Platinum Properties", company_id="company_properties", cash=250000)
    holding = HoldingCompany(name="Platinum Holdings", holding_company_id="holding_platinum")
    player = Player(name="Sam", player_id="player_sam", holding_company=holding)

    division.add_branch(branch)
    company.add_division(division)
    holding.add_company(company)

    assert player.holding_company.get_company("company_properties") is company
    assert company.get_division("division_properties") is division
    assert division.get_branch("branch_new_york") is branch
    assert holding.division_count == 1
    assert holding.branch_count == 1


def test_company_tracks_cash_reputation_executives_divisions_and_assets() -> None:
    company = Company(name="Property Co", company_id="property", cash=1000000, reputation=64.0)
    executive = Executive(name="Alex Morgan", title="CEO", reputation=75.0)
    division = Division(name="Property", division_id="division_property")

    company.add_executive(executive)
    company.add_division(division)
    company.spend_cash(150000)
    company.add_cash(50000)
    company.set_reputation(70.0)

    assert company.cash == 900000
    assert company.reputation == 70.0
    assert company.executives == [executive]
    assert company.divisions == [division]
    assert company.total_cash() == 900000


def test_company_rejects_invalid_cash_and_reputation() -> None:
    try:
        Company(name="Bad Cash", cash=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected negative company cash to be rejected.")

    try:
        Company(name="Bad Reputation", reputation=101.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected reputation over 100 to be rejected.")


def test_company_round_trips_property_shape_through_dict() -> None:
    company = Company(name="Serializable Property Co", company_id="serial", cash=500000, reputation=80.0)
    company.add_executive(
        Executive(
            name="Jamie Lee",
            title="Property Director",
            salary=180000,
            loyalty=70.0,
            traits=("disciplined",),
            skills=SkillRatings(leadership=80.0, operations=75.0),
        )
    )
    company.add_division(
        Division(
            name="Expansion",
            division_id="division_expansion",
            branches=[Branch(name="Los Angeles Branch", branch_id="branch_los_angeles", city_id="los_angeles")],
        )
    )

    loaded = Company.from_dict(company.to_dict())

    assert loaded.company_id == "serial"
    assert loaded.executives[0].title == "Property Director"
    assert loaded.executives[0].salary == 180000
    assert loaded.executives[0].traits == ("disciplined",)
    assert loaded.divisions[0].branches[0].city_id == "los_angeles"


def test_game_state_save_round_trips_player_company_hierarchy() -> None:
    with TemporaryDirectory() as directory:
        state = GameState(world_id="company-save", world_name="Company Save")
        company = Company(name="Saved Property Co", company_id="saved", cash=750000)
        company.add_division(
            Division(
                name="Saved Division",
                division_id="saved_division",
                branches=[Branch(name="Saved Branch", branch_id="saved_branch")],
            )
        )
        state.player.holding_company.add_company(company)

        manager = SaveManager(save_root=Path(directory))
        manager.save_world(state, slot_name="companies")
        loaded = manager.load_world("company-save", slot_name="companies")

    loaded_company = loaded.player.holding_company.get_company("saved")
    assert loaded_company is not None
    assert loaded_company.cash == 750000
    assert loaded_company.get_division("saved_division") is not None
    assert loaded.player.holding_company.branch_count == 1


def test_skill_ratings_validate_zero_to_100_scale() -> None:
    skills = SkillRatings(leadership=90.0, finance=80.0)

    assert skills.average > 50.0

    try:
        SkillRatings(operations=101.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected skill ratings above 100 to be rejected.")


def test_executives_provide_property_company_boosts_from_skills() -> None:
    executive = Executive(
        name="Priya Shah",
        title="Property Strategist",
        skills=SkillRatings(
            leadership=90.0,
            finance=85.0,
            operations=70.0,
            negotiation=95.0,
            innovation=88.0,
            people=75.0,
        ),
        salary=250000,
        loyalty=80.0,
        traits=("deal-maker",),
        workload_percent=90.0,
        reputation=82.0,
    )
    company = Company(name="Boosted Property Co", cash=1000000)

    company.add_executive(executive)
    boosts = company.aggregate_executive_boosts()

    assert boosts["reputation"] > 0
    assert boosts["profit"] > 0
    assert boosts["deal_quality"] > 0
