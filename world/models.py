# world/models.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class City:
    city_id: str
    name: str
    population: int
    property_multiplier: float
    growth_rate: float
    demand_score: float

    def __post_init__(self) -> None:
        if self.population < 0:
            raise ValueError(f"City population cannot be negative: {self.name}")

        for field_name in ("property_multiplier", "demand_score"):
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"City {field_name} cannot be negative: {self.name}")

        if self.growth_rate <= -1:
            raise ValueError(f"City growth_rate must be greater than -1: {self.name}")

    def projected_population(self, years: int = 1) -> int:
        if years < 0:
            raise ValueError("Population projection years cannot be negative.")

        return round(self.population * ((1 + self.growth_rate) ** years))

    def to_dict(self) -> dict[str, Any]:
        return {
            "city_id": self.city_id,
            "name": self.name,
            "population": self.population,
            "property_multiplier": self.property_multiplier,
            "growth_rate": self.growth_rate,
            "demand_score": self.demand_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> City:
        return cls(
            city_id=str(data["city_id"]),
            name=str(data["name"]),
            population=int(data["population"]),
            property_multiplier=float(data["property_multiplier"]),
            growth_rate=float(data["growth_rate"]),
            demand_score=float(data["demand_score"]),
        )


@dataclass(slots=True)
class Region:
    region_id: str
    name: str
    cities: list[City] = field(default_factory=list)

    @property
    def population(self) -> int:
        return sum(city.population for city in self.cities)

    def get_city(self, city_id: str) -> City | None:
        return next((city for city in self.cities if city.city_id == city_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "name": self.name,
            "cities": [city.to_dict() for city in self.cities],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Region:
        return cls(
            region_id=str(data["region_id"]),
            name=str(data["name"]),
            cities=[City.from_dict(city) for city in data.get("cities", [])],
        )


@dataclass(slots=True)
class Country:
    country_id: str
    name: str
    iso_code: str
    currency_code: str
    regions: list[Region] = field(default_factory=list)

    @property
    def population(self) -> int:
        return sum(region.population for region in self.regions)

    @property
    def cities(self) -> tuple[City, ...]:
        return tuple(city for region in self.regions for city in region.cities)

    def get_region(self, region_id: str) -> Region | None:
        return next((region for region in self.regions if region.region_id == region_id), None)

    def get_city(self, city_id: str) -> City | None:
        for region in self.regions:
            city = region.get_city(city_id)
            if city is not None:
                return city
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "country_id": self.country_id,
            "name": self.name,
            "iso_code": self.iso_code,
            "currency_code": self.currency_code,
            "regions": [region.to_dict() for region in self.regions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Country:
        return cls(
            country_id=str(data["country_id"]),
            name=str(data["name"]),
            iso_code=str(data["iso_code"]),
            currency_code=str(data["currency_code"]),
            regions=[Region.from_dict(region) for region in data.get("regions", [])],
        )


@dataclass(slots=True)
class Continent:
    continent_id: str
    name: str
    countries: list[Country] = field(default_factory=list)

    @property
    def population(self) -> int:
        return sum(country.population for country in self.countries)

    @property
    def cities(self) -> tuple[City, ...]:
        return tuple(city for country in self.countries for city in country.cities)

    def get_country(self, country_id: str) -> Country | None:
        return next((country for country in self.countries if country.country_id == country_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "continent_id": self.continent_id,
            "name": self.name,
            "countries": [country.to_dict() for country in self.countries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Continent:
        return cls(
            continent_id=str(data["continent_id"]),
            name=str(data["name"]),
            countries=[Country.from_dict(country) for country in data.get("countries", [])],
        )


@dataclass(slots=True)
class World:
    continents: list[Continent] = field(default_factory=list)

    @property
    def countries(self) -> tuple[Country, ...]:
        return tuple(country for continent in self.continents for country in continent.countries)

    @property
    def cities(self) -> tuple[City, ...]:
        return tuple(city for country in self.countries for city in country.cities)

    @property
    def population(self) -> int:
        return sum(country.population for country in self.countries)

    def get_continent(self, continent_id: str) -> Continent | None:
        return next(
            (continent for continent in self.continents if continent.continent_id == continent_id),
            None,
        )

    def get_country(self, country_id: str) -> Country | None:
        for continent in self.continents:
            country = continent.get_country(country_id)
            if country is not None:
                return country
        return None

    def get_city(self, city_id: str) -> City | None:
        for country in self.countries:
            city = country.get_city(city_id)
            if city is not None:
                return city
        return None

    def add_country(self, continent_id: str, country: Country) -> None:
        continent = self.get_continent(continent_id)
        if continent is None:
            raise ValueError(f"Unknown continent: {continent_id}")

        if self.get_country(country.country_id) is not None:
            raise ValueError(f"Country already exists: {country.country_id}")

        continent.countries.append(country)

    def to_dict(self) -> dict[str, Any]:
        return {
            "continents": [continent.to_dict() for continent in self.continents],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> World:
        return cls(
            continents=[Continent.from_dict(continent) for continent in data.get("continents", [])]
        )
