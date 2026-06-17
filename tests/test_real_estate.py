# tests/test_real_estate.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from industries.real_estate.industry import RealEstateIndustry
from industries.real_estate.models import Occupancy, Property, Tenant
from world.system import WorldSystem


def test_real_estate_config_loads_building_types() -> None:
    industry = RealEstateIndustry()

    building_type = industry.building_types["small_office"]

    assert industry.display_name == "Real Estate"
    assert building_type.name == "Small Office"
    assert building_type.base_construction_cost == 500000
    assert building_type.tenant_capacity == 6


def test_city_cost_multipliers_affect_cost_rent_and_value() -> None:
    world = WorldSystem.starter_world()
    detroit = world.get_city("detroit")
    new_york = world.get_city("new_york_city")
    building_type = RealEstateIndustry().building_types["office_tower"]

    assert detroit is not None
    assert new_york is not None
    assert building_type.city_construction_cost(new_york) > building_type.city_construction_cost(detroit)
    assert building_type.city_monthly_rent(new_york) > building_type.city_monthly_rent(detroit)
    assert building_type.city_property_value(new_york) > building_type.city_property_value(detroit)


def test_property_tracks_tenants_occupancy_rent_maintenance_and_value() -> None:
    world = WorldSystem.starter_world()
    city = world.get_city("new_york_city")
    industry = RealEstateIndustry()
    building_type = industry.building_types["small_office"]
    property_ = Property(
        name="New York Offices",
        building_type=building_type,
        city_id="new_york_city",
        property_id="property_new_york",
    )

    property_.add_tenant(Tenant(name="Anchor Tenant", monthly_rent=12000, tenant_id="tenant_anchor"))
    property_.add_tenant(Tenant(name="Second Tenant", monthly_rent=9000, tenant_id="tenant_second"))

    assert city is not None
    assert property_.occupancy == Occupancy(occupied_units=2, total_units=6)
    assert property_.occupancy.rate == 2 / 6
    assert property_.monthly_rent(city) >= 21000
    assert property_.monthly_maintenance(city) > 0
    assert property_.property_value(city) > 0
    assert property_.monthly_net_income(city) == property_.monthly_rent(city) - property_.monthly_maintenance(city)


def test_real_estate_industry_tracks_portfolio_value_and_income() -> None:
    world = WorldSystem.starter_world()
    industry = RealEstateIndustry()
    property_ = industry.create_property(
        name="Los Angeles Tower",
        building_type_id="office_tower",
        city_id="los_angeles",
    )
    property_.add_tenant(Tenant(name="Prime Tenant", monthly_rent=175000))

    assert industry.total_property_value(world) > 0
    assert industry.monthly_net_income(world) > 0


def test_property_round_trips_through_dict_with_configured_building_type() -> None:
    industry = RealEstateIndustry()
    property_ = Property(
        name="Warehouse",
        building_type=industry.building_types["industrial_warehouse"],
        city_id="chicago",
        property_id="property_warehouse",
        tenants=[Tenant(name="Logistics Tenant", monthly_rent=25000, tenant_id="tenant_logistics")],
        condition=0.92,
        expected_occupancy=0.86,
        actual_occupancy=0.79,
    )

    loaded = Property.from_dict(
        data=property_.to_dict(),
        building_types=industry.building_types,
    )

    assert loaded.property_id == "property_warehouse"
    assert loaded.building_type.building_type_id == "industrial_warehouse"
    assert loaded.tenants[0].tenant_id == "tenant_logistics"
    assert loaded.condition == 0.92
    assert loaded.expected_occupancy == 0.86
    assert loaded.actual_occupancy == 0.79
