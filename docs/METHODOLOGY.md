# Methodology

The simulation advances in one-hour steps. A dust-perturbed lunar daylight
curve supplies power. The scheduler holds a battery reserve, then allocates
energy to regolith processing, metal-fed printing, and excavation according to
inventory targets. Electrolysis co-produces oxygen and a metal-feedstock proxy;
printing has a yield loss. Rare seeded downtime events affect all processing.

Every operation is constrained by available energy, input inventory, equipment
throughput, and storage state. Tests enforce non-negative inventory and bound
energy consumption by solar generation plus the initial battery charge.
