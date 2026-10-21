import pytest

from model import (MiningSystem, RegolithSite, Terrain, adaptive_process_plan,
                   leave_one_site_out_validation, reliability_ensemble, simulate,
                   solar_output, specific_mining_energy)


def test_solar_output_is_bounded():
    assert all(0 <= solar_output(h, 30) <= 30 for h in range(708))


def test_simulation_is_reproducible():
    assert simulate(seed=4) == simulate(seed=4)


def test_mass_and_energy_are_nonnegative_and_conserved():
    result = simulate(hours=160)
    assert result.excavated_kg == pytest.approx(result.delivered_regolith_kg + result.unhauled_regolith_kg)
    assert min(result.delivered_regolith_kg, result.energy_generated_kwh, result.energy_used_kwh) >= 0


def test_harder_terrain_costs_more_energy_per_kg():
    easy = specific_mining_energy(MiningSystem(), Terrain(slope_degrees=2, compaction_factor=0.9))
    hard = specific_mining_energy(MiningSystem(), Terrain(slope_degrees=14, compaction_factor=1.5))
    assert hard > easy


def test_more_solar_does_not_reduce_delivered_output():
    low = simulate(hours=240, system=MiningSystem(solar_kw=12), seed=5)
    high = simulate(hours=240, system=MiningSystem(solar_kw=42), seed=5)
    assert high.delivered_regolith_kg >= low.delivered_regolith_kg


def test_invalid_horizon_rejected():
    with pytest.raises(ValueError):
        simulate(hours=0)


def test_reliability_ensemble_reports_ordered_quantiles():
    out = reliability_ensemble(draws=20, hours=100)
    assert out["p10_delivered_kg"] <= out["mean_delivered_kg"] <= out["p90_delivered_kg"]


def test_composition_aware_process_selection_changes_by_site():
    glassy = RegolithSite("glassy", .85, .2, .6, .2)
    oxide_rich = RegolithSite("oxide", .2, .9, .6, .2)
    assert adaptive_process_plan(glassy, 1000).process != adaptive_process_plan(oxide_rich, 1000).process


def test_leave_one_site_out_validation_never_hides_adaptive_loss():
    sites = [
        RegolithSite("mare", .55, .75, .55, .3),
        RegolithSite("highland", .78, .35, .72, .2),
        RegolithSite("mixed", .42, .62, .88, .1),
        RegolithSite("rough", .32, .48, .30, .5),
    ]
    results = leave_one_site_out_validation(sites)
    assert len(results) == len(sites)
    assert all(result["adaptive_gain"] >= -1e-12 for result in results)
