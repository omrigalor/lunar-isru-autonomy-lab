"""Energy- and reliability-constrained lunar regolith mining simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import random


@dataclass(frozen=True)
class MiningSystem:
    solar_kw: float = 28.0
    battery_kwh: float = 150.0
    excavator_kg_h: float = 20.0
    haul_payload_kg: float = 55.0
    excavation_kwh_kg: float = 0.10
    crusher_kwh_kg: float = 0.05
    traverse_kwh_km: float = 0.85
    one_way_haul_km: float = 1.4
    wear_limit: float = 100.0


@dataclass(frozen=True)
class Terrain:
    slope_degrees: float = 7.0
    compaction_factor: float = 1.15
    boulder_probability_h: float = 0.025
    dust_transmission_mean: float = 0.86


@dataclass(frozen=True)
class MiningResult:
    excavated_kg: float
    delivered_regolith_kg: float
    unhauled_regolith_kg: float
    energy_generated_kwh: float
    energy_used_kwh: float
    curtailed_kwh: float
    boulder_delay_hours: int
    maintenance_hours: int
    final_wear_index: float
    delivered_kg_per_operating_hour: float


@dataclass(frozen=True)
class RegolithSite:
    name: str
    glass_fraction: float
    metal_oxide_fraction: float
    grain_uniformity: float
    haul_km: float


@dataclass(frozen=True)
class FabricationProcess:
    name: str
    base_kwh_kg: float
    imported_consumables_kg_per_kg: float
    glass_weight: float
    oxide_weight: float
    uniformity_weight: float


@dataclass(frozen=True)
class FabricationPlan:
    site: str
    process: str
    usable_print_mass_kg: float
    energy_kwh: float
    imported_consumables_kg: float
    quality_score: float
    objective: float


PROCESSES = (
    FabricationProcess("adaptive laser vitrification", 0.90, 0.0, 0.65, 0.15, 0.20),
    FabricationProcess("pulsed electrical discharge", 0.72, 0.0, 0.25, 0.55, 0.20),
    FabricationProcess("microwave sintering", 1.05, 0.0, 0.30, 0.30, 0.40),
)


def solar_output(hour: int, capacity_kw: float, dust_factor: float = 1.0) -> float:
    """Illustrative half-sine daylight profile over a 708-hour lunar cycle."""
    phase = 2 * math.pi * ((hour + 90) % 708) / 708
    return capacity_kw * max(0.0, math.sin(phase)) * dust_factor


def specific_mining_energy(system: MiningSystem, terrain: Terrain) -> float:
    """Energy per delivered kilogram, including excavation, crushing, and haul."""
    slope_multiplier = 1.0 + 0.018 * max(0.0, terrain.slope_degrees)
    dig = system.excavation_kwh_kg * terrain.compaction_factor * slope_multiplier
    round_trip = 2 * system.one_way_haul_km * system.traverse_kwh_km
    haul = round_trip / system.haul_payload_kg
    return dig + system.crusher_kwh_kg + haul


def simulate(hours: int = 336, system: MiningSystem = MiningSystem(),
             terrain: Terrain = Terrain(), seed: int = 17) -> MiningResult:
    if hours < 1:
        raise ValueError("hours must be positive")
    if min(asdict(system).values()) <= 0:
        raise ValueError("mining-system parameters must be positive")
    if terrain.slope_degrees < 0 or terrain.compaction_factor <= 0:
        raise ValueError("terrain parameters are invalid")
    if not 0 <= terrain.boulder_probability_h < 1:
        raise ValueError("boulder probability must be in [0, 1)")

    rng = random.Random(seed)
    battery = system.battery_kwh / 2
    stock = excavated = delivered = generated = used = curtailed = wear = 0.0
    boulder_delay = maintenance = 0
    energy_per_kg = specific_mining_energy(system, terrain)

    for hour in range(hours):
        dust = min(1.0, max(0.35, rng.gauss(terrain.dust_transmission_mean, 0.08)))
        solar = solar_output(hour, system.solar_kw, dust)
        generated += solar
        reserve = 0.22 * system.battery_kwh
        available = solar + max(0.0, battery - reserve)

        if wear >= system.wear_limit:
            maintenance += 1
            wear *= 0.35
            demand = 0.0
        elif rng.random() < terrain.boulder_probability_h:
            boulder_delay += 1
            wear += 0.8
            demand = 0.0
        else:
            thermal_phase = 2 * math.pi * (hour % 708) / 708
            thermal_derating = 0.80 + 0.20 * (1 + math.cos(thermal_phase)) / 2
            wear_derating = max(0.55, 1 - 0.004 * wear)
            capacity = system.excavator_kg_h * thermal_derating * wear_derating
            mined = min(capacity, available / energy_per_kg)
            demand = mined * energy_per_kg
            excavated += mined
            stock += mined
            wear += mined * (0.065 * terrain.compaction_factor)
            deliverable = min(stock, system.haul_payload_kg)
            delivered += deliverable
            stock -= deliverable

        solar_used = min(solar, demand)
        battery = max(0.0, battery - max(0.0, demand - solar_used))
        surplus = max(0.0, solar - solar_used)
        stored = min(surplus, system.battery_kwh - battery)
        battery += stored
        curtailed += surplus - stored
        used += demand

    operating = max(1, hours - boulder_delay - maintenance)
    return MiningResult(
        excavated_kg=excavated,
        delivered_regolith_kg=delivered,
        unhauled_regolith_kg=stock,
        energy_generated_kwh=generated,
        energy_used_kwh=used,
        curtailed_kwh=curtailed,
        boulder_delay_hours=boulder_delay,
        maintenance_hours=maintenance,
        final_wear_index=wear,
        delivered_kg_per_operating_hour=delivered / operating,
    )


def reliability_ensemble(draws: int = 200, hours: int = 336,
                         system: MiningSystem = MiningSystem(),
                         terrain: Terrain = Terrain(), seed: int = 17) -> dict[str, float]:
    if draws < 10:
        raise ValueError("use at least ten draws")
    values = sorted(simulate(hours, system, terrain, seed + i).delivered_regolith_kg
                    for i in range(draws))
    return {
        "mean_delivered_kg": sum(values) / draws,
        "p10_delivered_kg": values[int(0.1 * draws)],
        "p90_delivered_kg": values[min(draws - 1, int(0.9 * draws))],
    }


def plan_local_fabrication(
    site: RegolithSite,
    delivered_regolith_kg: float,
    process: FabricationProcess,
) -> FabricationPlan:
    """Score binder-free local printing after mining and short-haul penalties."""
    if delivered_regolith_kg <= 0:
        raise ValueError("delivered regolith must be positive")
    composition_fit = (
        process.glass_weight * site.glass_fraction
        + process.oxide_weight * site.metal_oxide_fraction
        + process.uniformity_weight * site.grain_uniformity
    )
    quality = min(1.0, max(0.0, 0.35 + 0.65 * composition_fit))
    usable = delivered_regolith_kg * (0.58 + 0.37 * quality)
    energy = usable * process.base_kwh_kg * (1.12 - 0.24 * composition_fit)
    # Mine-near-print removes most haul energy; residual distance remains visible.
    energy += usable * site.haul_km * 0.012
    imports = usable * process.imported_consumables_kg_per_kg
    objective = usable * quality / (energy + 35.0 * imports + 1e-9)
    return FabricationPlan(site.name, process.name, usable, energy, imports, quality, objective)


def adaptive_process_plan(
    site: RegolithSite,
    delivered_regolith_kg: float,
    processes: tuple[FabricationProcess, ...] = PROCESSES,
) -> FabricationPlan:
    """Choose the lowest-energy, highest-quality process for local composition."""
    return max(
        (plan_local_fabrication(site, delivered_regolith_kg, process) for process in processes),
        key=lambda plan: plan.objective,
    )


def leave_one_site_out_validation(
    sites: list[RegolithSite], delivered_regolith_kg: float = 1000.0
) -> list[dict[str, float | str]]:
    """Validate process selection on each composition held out in turn."""
    if len(sites) < 3:
        raise ValueError("at least three sites are required")
    results = []
    for held_out in sites:
        training = [site for site in sites if site != held_out]
        process_scores = {
            process: sum(
                plan_local_fabrication(site, delivered_regolith_kg, process).objective
                for site in training
            ) / len(training)
            for process in PROCESSES
        }
        fixed = max(process_scores, key=process_scores.get)
        fixed_plan = plan_local_fabrication(held_out, delivered_regolith_kg, fixed)
        adaptive = adaptive_process_plan(held_out, delivered_regolith_kg)
        results.append({
            "held_out_site": held_out.name,
            "fixed_process": fixed.name,
            "adaptive_process": adaptive.process,
            "fixed_objective": fixed_plan.objective,
            "adaptive_objective": adaptive.objective,
            "adaptive_gain": adaptive.objective - fixed_plan.objective,
        })
    return results


if __name__ == "__main__":
    print(json.dumps(asdict(simulate()), indent=2))
