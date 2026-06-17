# tests/test_world.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from core.save_manager import SaveManager
from core.state import GameState
from world.models import City, Country, Region
from world.system import WorldSystem


def test_starter_world_loads_american_city_market() -> None:
    world = WorldSystem.starter_world()
    country_ids = {country.country_id for country in world.countries}
    city_ids = {city.city_id for city in world.cities}

    assert "united_states" in country_ids
    assert country_ids == {"united_states"}
    assert {"new_york_city", "los_angeles", "chicago", "dallas", "miami"}.issubset(city_ids)
    assert len(world.cities) >= 60
    assert all(city.population >= 1_000_000 for city in world.cities)


def test_city_contains_required_market_fields() -> None:
    world = WorldSystem.starter_world()
    city = world.get_city("new_york_city")

    assert city is not None
    assert city.population > 0
    assert city.property_multiplier > 0
    assert city.growth_rate > 0
    assert 0 <= city.demand_score <= 100


def test_world_supports_future_country_expansion() -> None:
    world = WorldSystem.starter_world()
    country = Country(
        country_id="testland",
        name="Testland",
        iso_code="TL",
        currency_code="TST",
        regions=[
            Region(
                region_id="capital_region",
                name="Capital Region",
                cities=[
                    City(
                        city_id="test_city",
                        name="Test City",
                        population=500000,
                        property_multiplier=1.0,
                        growth_rate=0.02,
                        demand_score=55.0,
                    )
                ],
            )
        ],
    )

    world.add_country(continent_id="north_america", country=country)

    assert world.get_country("testland") is country
    assert world.get_city("test_city") is not None


def test_world_loads_from_json_configuration() -> None:
    payload = {
        "schema": "corp-sim-world",
        "version": 1,
        "world": {
            "continents": [
                {
                    "continent_id": "antarctica",
                    "name": "Antarctica",
                    "countries": [
                        {
                            "country_id": "research_zone",
                            "name": "Research Zone",
                            "iso_code": "AQ",
                            "currency_code": "USD",
                            "regions": [
                                {
                                    "region_id": "base_region",
                                    "name": "Base Region",
                                    "cities": [
                                        {
                                            "city_id": "base_city",
                                            "name": "Base City",
                                            "population": 1000,
                                            "property_multiplier": 0.5,
                                            "growth_rate": 0.0,
                                            "demand_score": 10.0,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    }

    with TemporaryDirectory() as directory:
        path = Path(directory) / "world.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        world = WorldSystem.from_config(path)

    assert world.get_country("research_zone") is not None
    assert world.get_city("base_city") is not None


def test_game_state_save_round_trips_world_data() -> None:
    with TemporaryDirectory() as directory:
        manager = SaveManager(save_root=Path(directory))
        state = GameState(world_id="world-save", world_name="World Save")

        manager.save_world(state, slot_name="starter")
        loaded = manager.load_world("world-save", slot_name="starter")

    assert loaded.world.get_city("new_york_city") is not None
    assert loaded.world.get_country("united_states") is not None
    assert len(loaded.world.countries) == len(state.world.countries)
