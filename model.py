"""Integrated lunar in-situ resource utilization scheduling simulator."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import math
import random


@dataclass(frozen=True)
class Plant:
    solar_kw: float = 32.0
    battery_kwh: float = 180.0
    excavator_kg_h: float = 16.0
    electrolysis_kg_h: float = 7.0
    printer_kg_h: float = 1.2
    mining_kwh_kg: float = 0.12
    electrolysis_kwh_kg: float = 2.2
    printing_kwh_kg: float = 3.8


@dataclass
class Inventory:
    raw_regolith_kg: float = 0.0
    oxygen_kg: float = 0.0
    metal_feedstock_kg: float = 0.0
    printed_parts_kg: float = 0.0
    battery_kwh: float = 90.0


@dataclass(frozen=True)
class MissionResult:
    oxygen_kg: float
    printed_parts_kg: float
    unprocessed_regolith_kg: float
    energy_generated_kwh: float
    energy_used_kwh: float
    curtailed_kwh: float
    downtime_hours: int
    earth_launch_displacement_kg: float


def solar_output(hour: int, capacity_kw: float, dust_factor: float = 1.0) -> float:
    """Illustrative half-sine daylight profile over a 29.5-day lunar cycle."""
    phase = 2 * math.pi * ((hour + 90) % 708) / 708
    return capacity_kw * max(0.0, math.sin(phase)) * dust_factor


def simulate(hours: int = 336, plant: Plant = Plant(), seed: int = 9,
             autonomous_scheduler: bool = True) -> MissionResult:
    if hours < 1 or min(asdict(plant).values()) <= 0:
        raise ValueError("positive horizon and plant parameters are required")
    rng = random.Random(seed)
    inv = Inventory(battery_kwh=plant.battery_kwh / 2)
    generated = used = curtailed = 0.0
    downtime = 0
    for hour in range(hours):
        dust = max(.45, min(1.0, rng.gauss(.88, .07)))
        available = solar_output(hour, plant.solar_kw, dust)
        generated += available
        # Rare common-mode outage; autonomy keeps reserves rather than consuming blindly.
        failed = rng.random() < .018
        if failed:
            downtime += 1
        reserve = .22 * plant.battery_kwh if autonomous_scheduler else 0.0
        draw = max(0.0, inv.battery_kwh - reserve)
        budget = available + draw
        demand_used = 0.0
        if not failed:
            oxygen_target = 90 + hour * .08
            parts_target = 18 + hour * .018
            # Process existing stock before mining more material.
            if inv.raw_regolith_kg > 0 and (inv.oxygen_kg < oxygen_target or not autonomous_scheduler):
                process = min(plant.electrolysis_kg_h, inv.raw_regolith_kg,
                              budget / plant.electrolysis_kwh_kg)
                energy = process * plant.electrolysis_kwh_kg
                inv.raw_regolith_kg -= process
                inv.oxygen_kg += process * .42
                inv.metal_feedstock_kg += process * .34
                budget -= energy; demand_used += energy
            if inv.metal_feedstock_kg > 0 and (inv.printed_parts_kg < parts_target or not autonomous_scheduler):
                feed = min(plant.printer_kg_h, inv.metal_feedstock_kg,
                           budget / plant.printing_kwh_kg)
                energy = feed * plant.printing_kwh_kg
                inv.metal_feedstock_kg -= feed
                inv.printed_parts_kg += feed * .82
                budget -= energy; demand_used += energy
            stock_target = 35 if autonomous_scheduler else 120
            if inv.raw_regolith_kg < stock_target:
                mined = min(plant.excavator_kg_h, budget / plant.mining_kwh_kg)
                energy = mined * plant.mining_kwh_kg
                inv.raw_regolith_kg += mined
                budget -= energy; demand_used += energy
        solar_used = min(available, demand_used)
        battery_used = max(0.0, demand_used - solar_used)
        inv.battery_kwh = max(0.0, inv.battery_kwh - battery_used)
        surplus = max(0.0, available - solar_used)
        stored = min(surplus, plant.battery_kwh - inv.battery_kwh)
        inv.battery_kwh += stored
        curtailed += surplus - stored
        used += demand_used
        if min(asdict(inv).values()) < -1e-9:
            raise AssertionError("inventory conservation violated")
    displacement = inv.oxygen_kg + inv.printed_parts_kg
    return MissionResult(inv.oxygen_kg, inv.printed_parts_kg, inv.raw_regolith_kg,
                         generated, used, curtailed, downtime, displacement)


def reliability_ensemble(draws: int = 200, hours: int = 336,
                         plant: Plant = Plant(), seed: int = 9) -> dict[str, float]:
    if draws < 10:
        raise ValueError("use at least ten draws")
    values = sorted(simulate(hours, plant, seed + i).earth_launch_displacement_kg
                    for i in range(draws))
    return {"mean_displacement_kg": sum(values) / draws,
            "p10_displacement_kg": values[int(.1 * draws)],
            "p90_displacement_kg": values[int(.9 * draws) - 1]}


if __name__ == "__main__":
    print(json.dumps(asdict(simulate()), indent=2))
