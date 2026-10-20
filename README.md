# Lunar ISRU Autonomy Lab

An integrated mission simulator connecting lunar regolith excavation, oxygen
and metal co-production, additive manufacturing, solar power, battery reserves,
dust uncertainty, and equipment downtime.

![ISRU system architecture](assets/reference.svg)

```bash
python -m pip install -e .
python model.py
pytest -q
```

## Research thesis

Individual ISRU components can look efficient while the system fails. A printer
without metal feedstock waits; electrolysis without excavated stock waits; an
excavator that consumes the night reserve can strand higher-value processes.
This prototype treats the plant as one inventory-and-energy network. The
autonomous scheduler maintains a battery reserve, processes bottleneck stock,
and targets oxygen and replacement-part inventories before mining excess mass.

Outputs include oxygen, printed parts, unprocessed inventory, energy use,
curtailment, downtime, and an explicit Earth-launch-displacement proxy. A seeded
ensemble reports P10/P90 mission output under dust and outages.

## Evidence base

- NASA, “Production of Oxygen from Lunar Regolith using Molten Oxide
  Electrolysis” (2009): https://ntrs.nasa.gov/citations/20090018064
- NASA, ISRU capability state of the art and current work (2022):
  https://ntrs.nasa.gov/citations/20220006072
- ESA, molten-salt electrolysis for oxygen and metal from lunar regolith:
  https://www.esa.int/Enabling_Support/Space_Engineering_Technology/ESA_opens_oxygen_plant_making_air_out_of_moondust

## Limits

This is a low-order software research model, not lunar hardware or mission
planning software. Process yields and energy intensities are illustrative. It
omits granular mechanics, thermal-vacuum behavior, electrochemistry, radiation,
communications delay, spare-part criticality, landing-site geology, and safety
qualification. “Launch displacement” is a bookkeeping proxy, not a cost claim.
