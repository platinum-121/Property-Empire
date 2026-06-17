# world/system.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from world.models import City, Continent, Country, Region, World


class WorldSystem:
    """Loads and manages JSON-driven world configuration."""

    MIN_STARTER_CITY_POPULATION = 1_000_000

    def __init__(self, world: World | None = None) -> None:
        self.world = world or World()

    @classmethod
    def from_config(cls, config_path: Path | str) -> WorldSystem:
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        return cls(world=World.from_dict(cls._payload_to_world_data(data)))

    @classmethod
    def starter_world(cls) -> WorldSystem:
        resource = files("world").joinpath("starter_world.json")
        data = json.loads(resource.read_text(encoding="utf-8"))
        world_data = cls._payload_to_world_data(data)
        return cls(world=World.from_dict(cls._filter_starter_city_population(world_data)))

    @property
    def continents(self) -> tuple[Continent, ...]:
        return tuple(self.world.continents)

    @property
    def countries(self) -> tuple[Country, ...]:
        return self.world.countries

    @property
    def cities(self) -> tuple[City, ...]:
        return self.world.cities

    @property
    def population(self) -> int:
        return self.world.population

    def get_country(self, country_id: str) -> Country | None:
        return self.world.get_country(country_id)

    def get_continent(self, continent_id: str) -> Continent | None:
        return self.world.get_continent(continent_id)

    def get_city(self, city_id: str) -> City | None:
        return self.world.get_city(city_id)

    def city_context(self, city_id: str) -> tuple[Continent, Country, Region, City] | None:
        for continent in self.continents:
            for country in continent.countries:
                for region in country.regions:
                    city = region.get_city(city_id)
                    if city is not None:
                        return continent, country, region, city

        return None

    def add_country(self, continent_id: str, country: Country) -> None:
        self.world.add_country(continent_id=continent_id, country=country)

    def to_dict(self) -> dict[str, Any]:
        return self.world.to_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldSystem:
        return cls(world=World.from_dict(data))

    @staticmethod
    def _payload_to_world_data(data: dict[str, Any]) -> dict[str, Any]:
        if "world" in data:
            return dict(data["world"])

        return data

    @classmethod
    def _filter_starter_city_population(cls, data: dict[str, Any]) -> dict[str, Any]:
        filtered = {"continents": []}
        for continent in data.get("continents", []):
            continent_copy = dict(continent)
            continent_copy["countries"] = []
            for country in continent.get("countries", []):
                country_copy = dict(country)
                country_copy["regions"] = []
                for region in country.get("regions", []):
                    cities = [
                        city
                        for city in region.get("cities", [])
                        if int(city.get("population", 0)) >= cls.MIN_STARTER_CITY_POPULATION
                    ]
                    if cities:
                        region_copy = dict(region)
                        region_copy["cities"] = cities
                        country_copy["regions"].append(region_copy)
                if country_copy["regions"]:
                    continent_copy["countries"].append(country_copy)
            if continent_copy["countries"]:
                filtered["continents"].append(continent_copy)
        return filtered

    def generate_stub_world(self) -> None:
        self.world = self.starter_world().world


__all__ = ["City", "Continent", "Country", "Region", "World", "WorldSystem"]
