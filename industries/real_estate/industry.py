# industries/real_estate/industry.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from industries.real_estate.models import BuildingType, Property


class RealEstateIndustry:
    industry_id = "real_estate"
    display_name = "Real Estate"

    def __init__(
        self,
        building_types: dict[str, BuildingType] | None = None,
        properties: list[Property] | None = None,
    ) -> None:
        self.building_types = building_types or self.load_building_types()
        self.properties = properties or []

    @classmethod
    def load_building_types(cls) -> dict[str, BuildingType]:
        resource = files("industries.real_estate").joinpath("building_types.json")
        data = json.loads(resource.read_text(encoding="utf-8"))
        return {
            building_type.building_type_id: building_type
            for building_type in (
                BuildingType.from_dict(item)
                for item in data.get("building_types", [])
            )
        }

    def create_property(
        self,
        name: str,
        building_type_id: str,
        city_id: str,
    ) -> Property:
        building_type = self.building_types[building_type_id]
        property_ = Property(name=name, building_type=building_type, city_id=city_id)
        self.properties.append(property_)
        return property_

    def total_property_value(self, world: Any) -> int:
        return sum(
            property_.property_value(world.get_city(property_.city_id))
            for property_ in self.properties
            if world.get_city(property_.city_id) is not None
        )

    def monthly_net_income(self, world: Any) -> int:
        return sum(
            property_.monthly_net_income(world.get_city(property_.city_id))
            for property_ in self.properties
            if world.get_city(property_.city_id) is not None
        )

    def process_tick(self, engine: Any, days: int) -> None:
        _ = engine
        _ = days

    def ui_hooks(self) -> dict[str, Any]:
        return {
            "page": "real_estate",
            "building_types": tuple(self.building_types.keys()),
        }
