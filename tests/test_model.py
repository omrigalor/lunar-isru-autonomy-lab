import pytest

from model import Plant, reliability_ensemble, simulate, solar_output


def test_solar_output_is_bounded():
    assert all(0 <= solar_output(h, 30) <= 30 for h in range(708))


def test_simulation_is_reproducible():
    assert simulate(seed=4) == simulate(seed=4)


def test_inventories_and_energy_are_nonnegative():
    r = simulate(hours=120)
    assert min(r.oxygen_kg, r.printed_parts_kg, r.unprocessed_regolith_kg,
               r.energy_generated_kwh, r.energy_used_kwh) >= 0


def test_energy_accounting_is_bounded_by_supply_and_initial_battery():
    plant = Plant(battery_kwh=100)
    r = simulate(hours=200, plant=plant)
    assert r.energy_used_kwh <= r.energy_generated_kwh + plant.battery_kwh / 2 + 1e-9


def test_more_solar_increases_or_preserves_output():
    low = simulate(hours=240, plant=Plant(solar_kw=16), seed=5)
    high = simulate(hours=240, plant=Plant(solar_kw=45), seed=5)
    assert high.earth_launch_displacement_kg >= low.earth_launch_displacement_kg


def test_invalid_horizon_rejected():
    with pytest.raises(ValueError):
        simulate(hours=0)


def test_reliability_ensemble_reports_quantiles():
    out = reliability_ensemble(draws=20, hours=100)
    assert out["p10_displacement_kg"] <= out["mean_displacement_kg"] <= out["p90_displacement_kg"]
