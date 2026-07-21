# El Paso Rent vs. Area Median Income (AMI)

## Why this matters

This is a feasibility story, not an affordability story — and it's worth being precise about
the difference, because the two can look contradictory at first glance.

**Market rents in El Paso are, in most cases, already below what a household could afford at
100% of Area Median Income.** Using this week's snapshot of active RentCast listings and HUD's
FY2025 income limits for the El Paso, TX MSA (family median income: $72,800), roughly
**70% of listings rent below the AMI-affordable threshold** for their unit's imputed household
size (HUD/LIHTC convention: 1.5 persons per bedroom). Even under a stricter 1:1
bedrooms-to-persons assumption, more than half of listings still fall below their threshold.

That does **not** mean there's no housing need in El Paso, and it doesn't contradict needs
assessments showing significant unmet demand even below 70% AMI. Rent level and housing need
measure different things: a market can have a low average price and still be short of
available, decent units at that price, especially for household sizes and unit types the
existing stock doesn't match well. This dataset speaks to price level; it says nothing about
vacancy, unit condition, or match to household size, which is where the real shortage shows up.

**What low rents actually explain is why middle housing isn't getting built where it's already
legal.** Duplexes are by-right in R-4 and R-5, and ADUs are allowed citywide — the zoning
reform for those types is largely done. Triplexes are the one type that still needs a zoning
change (currently limited to apartment or commercial zoning). So for duplexes and ADUs, the
question isn't "why is this illegal," it's "why doesn't anyone build it." The answer is a
construction pro forma problem: new-build costs (land, shell, financing, permitting) have to
be covered by achievable rent, and when the market is already clearing $790–850/month for
existing studios and 1BRs, a newly built unit can't charge a premium just because it's new.
The revenue side of the pro forma is capped by what's already on the market, and in El Paso
that cap sits below what ground-up construction typically needs to break even — regardless of
zoning.

**That reframes what "reform" should mean here.** It's not primarily a legalization problem —
duplex and ADU zoning already allows the units this data suggests the market could support.
The two levers that follow from a feasibility constraint are:

- **Prioritize adaptive reuse over new construction.** Converting an existing structure skips
  most of the land and shell cost that sinks new-build pro formas, so it can pencil at rents
  that kill ground-up projects. This is why our framework treats conversions as able to
  support more units per structure (up to 8 in high-vacancy tracts) than we'd recommend for
  new construction — it's not a stylistic preference, it's the mechanism that makes low rents
  compatible with getting anything built at all.
- **Target cost-side reform for new construction, not use-side reform.** Since raising rents
  to cover cost isn't available in this market, the reform that matters is lowering what a
  project has to cover: parking minimums, permitting timelines and predictability, a
  prescriptive small-multifamily code path, fee waivers, or gap financing/subsidy for the
  by-right quadplex-in-R-4/R-5 case. Recommending "expand duplex allowances" restates law
  that already exists; recommending fee or process relief for the duplexes and ADUs already
  legal today is the version that could actually change what gets built.

In short: the needs assessment and this dataset aren't in tension. One says there isn't
enough of the right housing; this one says the market can't currently afford to build more
of it new, but could plausibly afford to convert it.

## Why "below AMI" doesn't mean every city should favor conversion

A natural objection: if market rent below 100% AMI turns out to be common everywhere (a
quick check against Lubbock and Austin suggests it might be — see below), why would this
argue for conversion-focused reform in El Paso specifically, rather than everywhere?

Because AMI is a *relative* benchmark — it scales with each metro's own income level — while
construction costs are much closer to a national number (materials, labor, and financing
costs vary by region, but nowhere near as much as incomes do). So "rent vs. 100% AMI" and
"rent vs. what it costs to build" are different questions that can point in opposite
directions. Austin's market rent sits *further* below its own AMI than El Paso's does (its
income levels are so much higher), but in absolute dollars Austin's rent comfortably clears
the cost of new construction, while El Paso's doesn't — consistent with Austin's real-world
construction boom (30,000+ units delivered in the past year, enough to push its own vacancy
to a decade high and rents down 6% year-over-year).

**What's specific to El Paso isn't "rent below AMI" — it's absolute rent low relative to
input costs that aren't set locally.** That's a much narrower, more defensible claim, and
it's the reason this repo treats the feasibility classification (rent vs. construction
breakeven) as the primary finding and the AMI comparison as useful context, not the headline.

A rough, non-rigorous check against two other Texas metros (Lubbock and Austin, using
RentCafe/Zumper estimates rather than our own RentCast pipeline, so not apples-to-apples)
suggests rent-below-100%-AMI is common across very different market types:

| Metro | 100% AMI, 4-person (monthly) | Approx. single-family rent | Rent vs. AMI |
|---|---|---|---|
| El Paso | $1,820 (FY2025 MFI $72,800) | ~$1,500 | −18% |
| Lubbock | $2,000 (FY2025 MFI $80,000) | ~$1,562 | −22% |
| Austin | $3,360 (FY2026 MFI $134,400) | ~$2,395 | −29% |

## Where this lives

This is a sub-project inside the [`rentcast_ep`](https://github.com/hoffmanap/rentcast_ep) repo,
living in the `ami-feasibility/` folder alongside the original rental market dashboard at the
repo root. Live page: **https://hoffmanap.github.io/rentcast_ep/ami-feasibility/**

| File | Location | Purpose |
|---|---|---|
| `rent_history.csv` | repo root | Raw weekly RentCast listing snapshots (Wednesdays), appended by `rent_tracker.py` |
| `rent_tracker.py` | repo root | Fetches up to 500 active El Paso listings from the RentCast API each week |
| `usps_vacancy_trend_by_tract.csv` | `ami-feasibility/` | Quarterly tract-level USPS residential vacancy rates |
| `household_demand_signals_by_tract.csv` | `ami-feasibility/` | Tract-level housing-demand signals (cost burden, overcrowding, `demand_score`) |
| `weekly_analysis.py` | `ami-feasibility/` | The Thursday job: hex-bins rent data, geocodes hexes to tracts (cached in `hex_tract_lookup.csv`), joins vacancy/demand, classifies feasibility, appends to `ami_affordability_history.csv`, writes `el_paso_rent_vs_ami.geojson`. Reads `rent_history.csv` from the repo root, so it must be run from there (the workflow does this) |
| `hex_tract_lookup.csv` | `ami-feasibility/` | Cache of hex → census tract GEOID, built and maintained automatically by `weekly_analysis.py` |
| `ami_affordability_history.csv` | `ami-feasibility/` | Weekly time series: % below AMI, % conversion-feasible, % new-construction-feasible |
| `el_paso_rent_vs_ami.geojson` | `ami-feasibility/` | Hex-binned (H3, resolution 8) rents, AMI comparison, and feasibility classification, refreshed weekly |
| `index.html` | `ami-feasibility/` | This project's page — rent vs. income limits & development feasibility map |
| `README.md` | `ami-feasibility/` | This file |
| `El_Paso_Middle_Housing_Feasibility_Sensitivity.xlsx` | `ami-feasibility/` | Proforma sensitivity model; source of the feasibility breakeven thresholds |
| `.github/workflows/ami_summary.yml` | **repo root** (required — Actions only scans this exact path) | Thursday job that runs `weekly_analysis.py` and commits results back |


## Methodology notes

- **AMI source:** HUD FY2025 income limits, El Paso, TX MSA, family median income $72,800.
  Household-size adjustment factors follow HUD's standard schedule (70/80/90/100/108/116% of
  the 4-person median for 1–6 person households). Affordability threshold = 30% of gross
  annual income, divided by 12.
- **Household size by bedroom count:** two conventions are reported side by side.
  - *Standard* — the HUD/LIHTC convention used to set actual affordable-housing rent
    limits: 1.5 persons per bedroom (studio = 1 person; fractional sizes interpolated
    between whole-person AMI thresholds).
  - *Simple* — bedrooms = persons (1BR = 1-person household, etc.), a more conservative,
    easier-to-communicate baseline that likely undercounts typical occupancy for family-sized
    units in a market with above-average household sizes.
- **Snapshot vs. stock:** every weekly figure reflects *active listings* (asking rents,
  turnover units) — not rents actually paid across the occupied housing stock. This likely
  understates affordability at the bottom of the market and may modestly overstate it at
  the top, since active listings skew toward newer/turnover units.
- **Data window:** the time series currently covers May 11 – July 15, 2026 (11 weekly
  snapshots). Early weeks should be read as a baseline rather than a settled trend; a few
  more months of data will make week-to-week movement more interpretable.

## Initial findings (as of the July 15, 2026 snapshot)

- Median asking rent, all bedroom counts: **$1,500/month**.
- **69.6%** of listings fall below their AMI-affordable threshold (standard convention);
  **56.3%** under the simple convention. This has held in the 70–74% / 55–61% range,
  respectively, across all 11 weeks — a stable pattern, not a one-off snapshot.
- By bedroom count, the pattern flips around 3–4 bedrooms:

  | Bedrooms | Median rent | % vs. AMI (standard) | % vs. AMI (simple) |
  |---|---|---|---|
  | Studio | $790 | −38% | −38% |
  | 1BR | $850 | −38% | −33% |
  | 2BR | $1,100 | −33% | −24% |
  | 3BR | $1,775 | −6% | +8% |
  | 4BR | $2,093 | −1% | +15% |
  | 5BR | $2,850 | +35% | +57% |

  Studios through 2-bedroom units — the sizes that map most directly onto ADUs, duplex
  units, and small infill product — rent well under what their household size could
  afford at 100% AMI, under either convention.

## Where conversion is necessary vs. where new construction is feasible

`index.html` includes a second view — **Development Feasibility** — that classifies each hex
by comparing its median rent per square foot against breakeven thresholds derived from our
proforma sensitivity model (`El_Paso_Middle_Housing_Feasibility_Sensitivity.xlsx`), rather than
just against AMI. This answers a different, more actionable question than the AMI comparison:
not "is this rent affordable," but "does this rent support building anything at all."

**How the thresholds were derived:** the proforma computes feasibility as a residual-land-value
gap (supportable development cost vs. actual cost + target land value), holding a fixed market
rent assumption ($1.65/SF/month) constant across scenarios. We inverted that logic — holding
every other input (hard costs, target land value, hurdle rate, vacancy, opex) at the model's
baseline for a **4-unit, El Paso infill lot (7,000 SF, 900 SF/unit)** — and solved for the
minimum rent per square foot needed to clear each of the model's own feasibility bands:

| Threshold | 4-Unit New Construction | 4-Unit Remodel |
|---|---|---|
| Feasible without subsidy (Gap ≥ −3%) | $1.53/SF/mo | $0.99/SF/mo |
| Feasible with subsidy (Gap ≥ −10%) | $1.44/SF/mo | $0.94/SF/mo |
| Below subsidy floor | Not feasible | Not feasible |

Each hex is classified into one of four categories using its median $/SF rent:

- **New construction feasible** — rent clears the $1.53/SF new-construction bar
- **Conversion feasible, new construction not** — rent is between $0.99 and $1.53/SF
- **Conversion feasible only with subsidy** — rent is between $0.94 and $0.99/SF
- **Neither pencils without subsidy** — rent is below $0.94/SF

**Finding:** as of the July 15, 2026 snapshot, **87.7% of listings sit in the "conversion
feasible, new construction not" band**. Only 4.3% clear the new-construction threshold, and
about 5% don't support even subsidized conversion. Notably, the proforma's own built-in market
rent assumption ($1.65/SF) sits *above* the 75th percentile of what RentCast shows El Paso
actually charging ($1.33/SF) — so the model's default scenario reads "Feasible" everywhere,
which is an artifact of an optimistic rent input, not a reflection of the real market. Running
actual hex-level rents through the same logic is what surfaces the split.

**Known limitations of this classification, to be aware of when using it for site selection:**

- **The high-vacancy cutoff (top quartile, ≥1.4%) is a data-driven default, not a formally
  adopted project threshold.** Adjust `HIGH_VACANCY_PERCENTILE` in `weekly_analysis.py` if the
  project settles on a different definition of "high-vacancy" for the 8-unit assumption.
- **The hex-to-tract geocoding step requires real internet access to the Census Geocoder**,
  which GitHub Actions runners have but a sandboxed analysis environment may not. Results are
  cached in `hex_tract_lookup.csv` and committed back to the repo each week, so this only
  needs to succeed once per hex, not every run.
- **Rent/SF is noisy at the listing level** — listings missing square footage are dropped, and
  rent/SF is clipped to a $0.30–$5.00 range to remove data-entry outliers before taking the
  hex median.
- **Uses the market-rate-only proforma scenario**, not the 80–100% AMI sliding-scale scenario,
  to keep the comparison to "can this be built at all" rather than "can this be built with an
  inclusionary requirement." The sliding-scale thresholds are in the workbook if a future
  version of this map should use them instead.
- **`ami_affordability_history.csv`'s early weeks (May–July 2026) don't have feasibility
  percentages** — those columns were added after the initial backfill, and backfilling them
  would require re-geocoding historical listings, which needs the same real internet access
  noted above. They'll populate naturally as `weekly_analysis.py` runs going forward.

## Data & attribution

Rental listing data sourced from [RentCast](https://rentcast.io). Income limits from
[HUD User](https://www.huduser.gov/portal/datasets/il.html). Vacancy and housing-demand
signals from project-collected USPS and Census ACS tract-level data.
