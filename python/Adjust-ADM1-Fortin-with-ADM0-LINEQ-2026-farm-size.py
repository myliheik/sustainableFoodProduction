#!/usr/bin/env python
"""
# 2026-07-15 MY
# 

This script constructs a harmonized global ADM1 farm-size dataset for 1992–2020 by combining
LINEQ country-level mean farm-size time series and Fortin ADM1 observations. 
Country series are interpolated to annual values using log-space PCHIP.
Where a country has insufficient LINEQ observations, the script falls back to a broader
SUBSUBREG trend derived from the median country trend within each subregion. Fortin ADM1
observations are then expanded to annual regional trajectories by anchoring on the observed
census year and propagating yearly changes using the reference trend. Remaining missing regions
are filled with geographically nearest or touching donor regions, with preference given to
donors from the same country and then the same SUBSUBREG. The final outputs are a GeoPackage
and a global raster with one band per year.

Notes:
If a country is totally missing, filling with neihgbouring countries or region is ok. 
But if a country has some regional information (census), but not for all regions, it means, 
that in that region there is no agriculture OR the region has < 2000ha of agricultural area, 
so not included in statistics. And we should not fill those regions.

But some countries may just simply lack census information. 

Should we fill these cases with e.g. country mean? NGA, BIH, BWA


"""

import numpy as np
import pandas as pd
import geopandas as gpd

from scipy.interpolate import PchipInterpolator

import pyreadr

from shapely.geometry import box
from shapely.strtree import STRtree



import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds


# ==========================================================
# Settings: we are interested in time range of 1992-2020
# ==========================================================

START_YEAR = 1992
END_YEAR = 2020

years = np.arange(START_YEAR, END_YEAR + 1)

# Make a dictionary of countries and their subsubregions from NatEarth:

fp = '/Users/myliheik/Documents/myPython/FAOSTAT_trade/data/gis/adm0_NatEarth_all_ids.shp'
gdf_world = gpd.read_file(fp)

countrySUBSUBREGdict = (
    gdf_world.drop_duplicates("iso_a3")
      .set_index("iso_a3")["subregion"]
      .to_dict()
)
print(f'{len(countrySUBSUBREGdict)} countries in my NatEarth based dictionary')


# Kosovo is found in Fortin, but not in LINEQ:
# Let's add Kosovo to the dictionary so it can use the trend from Southern Europe:
countrySUBSUBREGdict["XKX"] = "Southern Europe"
# And Mayotte (Overseas department and region of France) to "Eastern Africa":
countrySUBSUBREGdict["MYT"] = "Eastern Africa"
# Let's set Uzbekistan -> Eastern Europe, slowly increasing
countrySUBSUBREGdict["UZB"] = "Eastern Europe"
# Kazakhstan -> Eastern Europe, slowly increasing, this is tidyous...
countrySUBSUBREGdict["KAZ"] = "Eastern Europe"

# Tajikistan and Kyrgyzstan to Southern Asia (slowly decreasing):
countrySUBSUBREGdict["TJK"] = "Southern Asia"
countrySUBSUBREGdict["KGZ"] = "Southern Asia"
countrySUBSUBREGdict["TKM"] = "Southern Asia"


# GAUL is used to find out missing regions beyond Fortin and LINEQ
fp = '/Users/myliheik/Documents/GISdata/world/GAUL_2024_L2/GAUL_2024_L2.shp'
gaul = gpd.read_file(fp)
print(f'GAUL: {gaul['iso3_code'].nunique()} countries, {gaul['gaul2_code'].nunique()} regions')


# ==========================================================
# All functions used in the workflow
# ==========================================================


def interpolate_log_pchip(x, y, target_years):
    """
    Interpolate annual values using PCHIP in log-space and
    extrapolate linearly in log-space outside observed years.

    Parameters
    ----------
    x : array-like
        Observation years.
    y : array-like
        Positive observed farm-size values.
    target_years : array-like
        Years to estimate.

    Returns
    -------
    numpy.ndarray
        Interpolated/extrapolated annual values on original scale.
    """
    # Cast inputs to arrays and sort by year
    x = np.asarray(x)
    y = np.asarray(y)

    order = np.argsort(x)
    x = x[order]
    y = y[order]

    # Log interpolation requires strictly positive values
    if np.any(y <= 0):
        raise ValueError("Farm sizes must be positive.")

    logy = np.log(y)
    spline = PchipInterpolator(x, logy)

    out = np.empty(len(target_years), dtype=float)

    # Interpolation inside observed range
    inside = (target_years >= x[0]) & (target_years <= x[-1])
    out[inside] = spline(target_years[inside])

    # Extrapolation outside observed range using boundary log-growth rates
    if len(x) >= 2:
        first_rate = (logy[1] - logy[0]) / (x[1] - x[0])
        before = target_years < x[0]
        out[before] = logy[0] + (target_years[before] - x[0]) * first_rate

        last_rate = (logy[-1] - logy[-2]) / (x[-1] - x[-2])
        after = target_years > x[-1]
        out[after] = logy[-1] + (target_years[after] - x[-1]) * last_rate

    return np.exp(out)


def build_annual_trends(df, years):
    """
    Build annual trends for each row in a wide table using log-PCHIP.

    Parameters
    ----------
    df : pandas.DataFrame
        Rows are entities (countries/SUBSUBREGs), columns are observed years.
    years : array-like
        Annual years to estimate.

    Returns
    -------
    tuple[pandas.DataFrame, list]
        (annual trend table, list of skipped entities with <2 observations)
    """
    annual = {}
    skipped = []

    for idx, row in df.iterrows():
        # Keep observed years only
        s = row.dropna()

        # Need at least 2 points for interpolation/extrapolation
        if len(s) < 2:
            skipped.append(idx)
            continue

        x = s.index.astype(float).astype(int).values
        y = s.values.astype(float)

        annual[idx] = interpolate_log_pchip(x, y, years)

    annual = pd.DataFrame(annual, index=years).T

    return annual, skipped


def estimate_regions(
    country_series,
    subsubregion_series,
    countrySUBSUBREGdict,
    regional_df,
    start_year=1992,
    end_year=2020,
):
    """
    Estimate yearly ADM1 farm-size trajectories from one observed regional anchor
    and a reference trend (country first, then SUBSUBREG fallback).

    Parameters
    ----------
    country_series : pandas.DataFrame
        Country trend table indexed by ISO3, columns are years.
    subsubregion_series : pandas.DataFrame
        SUBSUBREG trend table indexed by SUBSUBREG, columns are years.
    countrySUBSUBREGdict : dict
        Mapping ISO3 -> SUBSUBREG.
    regional_df : pandas.DataFrame
        Input regional observations with columns ISO3, YEAR, FARMSIZE, ADM1_KEY.
    start_year : int
        First model year.
    end_year : int
        Last model year.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        (regional_estimates, unmatched_regions)
    """
    years = np.arange(start_year, end_year + 1)
    out = []
    unmatched = []

    for _, row in regional_df.iterrows():
        iso = row["ISO3"]
        obs_year = int(row["YEAR"])

        # Skip observations outside target window
        if obs_year < start_year or obs_year > end_year:
            continue

        obs_value = row["FARMSIZE"]

        # Skip non-positive or missing anchors
        if pd.isna(obs_value) or obs_value <= 0:
            continue

        # Prefer country trend when available
        if iso in country_series.index:
            trend = country_series.loc[iso]
        else:
            # Fallback to mapped SUBSUBREG trend
            subsubreg = countrySUBSUBREGdict.get(iso)

            #if subsubreg == "Southern Africa": # this got fixed alredy in subsubregion_series
            #    subsubreg = "Eastern Africa"
            if subsubreg == "Australia and New Zealand":
                pass
            elif subsubreg is None or subsubreg not in subsubregion_series.index:
                tmp = row.copy()
                tmp["UNMATCH_REASON"] = "Neither country nor SUBSUBREG trend found"
                unmatched.append(tmp)
                continue

            trend = subsubregion_series.loc[subsubreg]

        # Require valid trend value at anchor year
        if pd.isna(trend.loc[obs_year]) or trend.loc[obs_year] <= 0:
            continue

        # Build full annual trajectory from anchor
        regional = pd.Series(index=years, dtype=float)
        regional.loc[obs_year] = obs_value

        # Forward propagation with year-to-year trend growth
        for y in range(obs_year + 1, end_year + 1):
            growth = trend.loc[y] / trend.loc[y - 1]
            regional.loc[y] = regional.loc[y - 1] * growth

        # Backward propagation with inverse growth
        for y in range(obs_year - 1, start_year - 1, -1):
            growth = trend.loc[y] / trend.loc[y + 1]
            regional.loc[y] = regional.loc[y + 1] * growth

        out.append(
            pd.DataFrame(
                {
                    "ADM1_KEY": row["ADM1_KEY"],
                    "ISO3": iso,
                    "YEAR": years,
                    "FARMSIZE_EST": regional.values,
                }
            )
        )

    regional_estimates = (
        pd.concat(out, ignore_index=True)
        if out
        else pd.DataFrame(columns=["ADM1_KEY", "ISO3", "YEAR", "FARMSIZE_EST"])
    )

    unmatched_regions = (
        pd.DataFrame(unmatched)
        if unmatched
        else pd.DataFrame(columns=list(regional_df.columns) + ["UNMATCH_REASON"])
    )

    return regional_estimates, unmatched_regions


def fill_missing_regions(
    missing_gdf,
    regionalEstimates,
    group_col="ISO3",
    region_col="SUBSUBREG",
    year_cols=None,
    use_touching=True,
):
    """
    Fill missing ADM1 regions using nearest/touching donors from existing regions.

    Fill hierarchy
    --------------
    use_touching=True:
      1) touching donors in same country
      2) nearest donor in same country
      3) nearest donor in same SUBSUBREG
      4) fallback SUBSUBREG remap

    use_touching=False:
      1) nearest donor in same country
      2) nearest donor in same SUBSUBREG
      3) fallback SUBSUBREG remap

    Parameters
    ----------
    missing_gdf : geopandas.GeoDataFrame
        Regions with missing farm-size time series.
    regionalEstimates : geopandas.GeoDataFrame
        Regions with existing estimated time series.
    group_col : str
        Country grouping column.
    region_col : str
        Larger-region grouping column.
    year_cols : list[int] | None
        Year columns to transfer. Defaults to 1992..2020.
    use_touching : bool
        Whether to prefer touching neighbours.

    Returns
    -------
    geopandas.GeoDataFrame
        Input missing_gdf with filled values and metadata columns.
    """
    SUBSUBREG_FALLBACK = {
        "Central Asia": "Eastern Europe",
        "Seven seas (open ocean)": None,
    }

    if year_cols is None:
        year_cols = list(range(1992, 2021))

    numeric_cols = [c for c in year_cols + ["mean_1995_2005"] if c in regionalEstimates.columns]
    categorical_cols = [c for c in ["FARMSIZE_CAT"] if c in regionalEstimates.columns]

    out = missing_gdf.copy()
    source = regionalEstimates.copy()

    # CRS validation and harmonization
    if out.crs is None:
        raise ValueError("missing_gdf has no CRS.")
    if source.crs is None:
        raise ValueError("regionalEstimates has no CRS.")

    if out.crs != source.crs:
        source = source.to_crs(out.crs)

    # Use projected CRS for spatial neighbour operations
    if out.crs.is_geographic:
        out = out.to_crs(3857)
        source = source.to_crs(3857)

    out["missingInformationFrom"] = pd.NA
    out["fillMethod"] = pd.NA

    # Country-level cache with geometry index
    country_cache = {}
    for iso, grp in source.groupby(group_col):
        grp = grp.reset_index(drop=True)
        geoms = grp.geometry.to_numpy()
        country_cache[iso] = {"rows": grp, "geoms": geoms, "tree": STRtree(geoms)}

    # Region-level cache with geometry index
    region_cache = {}
    for reg, grp in source.groupby(region_col):
        grp = grp.reset_index(drop=True)
        geoms = grp.geometry.to_numpy()
        region_cache[reg] = {"rows": grp, "geoms": geoms, "tree": STRtree(geoms)}

    # Fill each missing polygon
    for row in out.itertuples():
        idx = row.Index
        geom = row.geometry
        iso = getattr(row, group_col)
        reg = getattr(row, region_col)

        donors = None
        method = None

        # Try country-level donors first
        if iso in country_cache:
            cache = country_cache[iso]
            rows = cache["rows"]
            geoms = cache["geoms"]
            tree = cache["tree"]

            if use_touching:
                candidate_idx = tree.query(geom)
                touching_idx = [i for i in candidate_idx if geoms[i].touches(geom)]

                if touching_idx:
                    donors = rows.iloc[touching_idx]
                    method = "touching_country"

            if donors is None:
                nearest_idx = tree.nearest(geom)
                donors = rows.iloc[[nearest_idx]]
                method = "nearest_country"

        # Fallback to region-level donors
        if donors is None:
            if reg not in region_cache:
                reg = SUBSUBREG_FALLBACK.get(reg)
                if reg is None or reg not in region_cache:
                    continue

            cache = region_cache[reg]
            rows = cache["rows"]
            tree = cache["tree"]

            nearest_idx = tree.nearest(geom)
            donors = rows.iloc[[nearest_idx]]
            method = "nearest_SUBSUBREG"

        # Transfer numeric means
        means = donors[numeric_cols].mean()
        for col in numeric_cols:
            out.at[idx, col] = means[col]

        # Transfer categorical mode
        for col in categorical_cols:
            mode = donors[col].mode()
            if len(mode):
                out.at[idx, col] = mode.iloc[0]

        out.at[idx, "missingInformationFrom"] = ";".join(donors["ADM1_KEY"].astype(str))
        out.at[idx, "fillMethod"] = method

    return out

# --------------------------------------------------
# LINEQ
# --------------------------------------------------

# LINEQ_V1_FINAL contains harmonized agricultural census and survey data on farm-size distributions and 
# structural indicators compiled by FAO's Global Database of Land Distribution and Inequality (LINEQ). 
# The dataset reports country- and census-specific estimates of agricultural structure, including the number of 
# holdings, total operated agricultural area, mean and median farm size, and related land-distribution statistics 
# reconstructed from grouped census tabulations using generalized Pareto interpolation.

# We will use LINEQ country records to extrapolate region records from Fortin data (see below).

# Read LINEQ data:
fp = '/Users/myliheik/Documents/myPython/sustainableFoodProduction/data/LINEQ_V1_FINAL.rds'

result = pyreadr.read_r(fp)
df = next(iter(result.values()))
print('FAO WCA rounds:')
print(f'From {int(df['wca_round'].min())} to {int(df['wca_round'].max())}')

dfLatest = df[df['wca_round'] >= 1990.0]

#print(len(dfLatest))
print(f"Unique countries: {len(dfLatest['iso03'].unique())}")

# pivot on iso03:
df_wide_country = (
    dfLatest.pivot_table(
        index="iso03",
        columns="source_year",
        values="lo_mean_all",
        aggfunc="first"
    )
    .rename_axis(columns=None)
    .reset_index()
)


# Building country trends (with interpolate_log_pchip), will need at least two observations

country_series = {}
no_country_trend_available = []

for _, row in df_wide_country.iterrows():

    iso = row["iso03"]

    s = row.drop("iso03").dropna()

    # need at least two observations
    if len(s) < 2:
        #print(f'{iso} has only {len(s)} observations, cannot build country trend!')
        no_country_trend_available.append(iso)
        continue

    x = s.index.astype(float).astype(int).values
    y = s.values.astype(float)

    annual = interpolate_log_pchip(
        x,
        y,
        years
    )

    country_series[iso] = annual



country_series = pd.DataFrame(
    country_series,
    index=years
).T

print(f'{len(df_wide_country)} countries were checked. {len(no_country_trend_available)} out of {len(df_wide_country)} has only 1 observations, cannot build country trend for them!')
print('We need to use SUBSUBREG trend for these.')


# For countries that do not exist in LINEQ we will need to use the SUBSUBREGION trend.
# Here we take the median of all countries within each SUBSUBREG and average by two periods: 
# start-2005 ja 2006-end, because some countries may be included only once, or have 
# much larger farm size than the rest of the subsubregion, so the trend gets really biased.

# Take all countries in LINEQ:
LINEQcountries = (
    df_wide_country
    .set_index("iso03")
    .rename_axis("ISO3")
)

LINEQcountries.columns = LINEQcountries.columns.astype(int)
LINEQcountries = LINEQcountries.apply(pd.to_numeric, errors="coerce")

# Median of all countries within each SUBSUBREG
year_cols = LINEQcountries.columns
subsubregion_series = (
    LINEQcountries
    .assign(SUBSUBREG=LINEQcountries.index.map(countrySUBSUBREGdict))
    .groupby("SUBSUBREG")[year_cols]
    .median(numeric_only=True)
    .sort_index()
)


df = subsubregion_series.copy()

# ensure year columns are integers
df.columns = pd.to_numeric(df.columns, errors="coerce").astype("Int64")
df = df.loc[:, df.columns.notna()]
df = df.reindex(columns=range(1986, 2024))

# compute the two period means
period_means = pd.DataFrame(index=df.index)
period_means["mean_1986_2005"] = df.loc[:, 1986:2005].mean(axis=1)
period_means["mean_2006_2023"] = df.loc[:, 2006:2023].mean(axis=1)

# build sparse 1986–2023 table
subsubregion_sparse = pd.DataFrame(
    np.nan,
    index=df.index,
    columns=range(1986, 2024),
    dtype=float
)

subsubregion_sparse[1990] = period_means["mean_1986_2005"]
subsubregion_sparse[2020] = period_means["mean_2006_2023"]
subsubregion_sparse.index.name = "SUBSUBREG"
subsubregion_series = subsubregion_sparse




# But the trend in Southern Africa does not look plausible so let's replace 'Southern Africa' by 'Middle Africa' (increasing)

# Replace values in "Southern Africa" row with values from "Middle Africa" x 5!
# This give more reliable trend of farm size when calculating trend for countries that don't have census records
# to calculate the trend.

if {"Middle Africa", "Southern Africa"}.issubset(subsubregion_series.index):
    subsubregion_series.loc["Southern Africa"] = subsubregion_series.loc["Middle Africa"].values * 5
else:
    missing = {"Southern Africa", "Middle Africa"} - set(subsubregion_series.index)
    raise KeyError(f"Missing index label(s): {missing}")



country_series, no_country_trend_available = build_annual_trends(
    df_wide_country.set_index("iso03"),
    years,
)

# Building SUBSUBREG trends (with interpolate_log_pchip), will use two averaged period observations 1990 and 2020:

subsubregion_series_sparse = subsubregion_series


subsubregion_series, no_subsubregion_trend_available = build_annual_trends(
    subsubregion_series_sparse,
    years
)

subsubregion_series = subsubregion_series.rename_axis("SUBSUBREG")


merged_country_subsub_series = pd.concat([country_series, subsubregion_series])



# --------------------------------------------------
# Fortin
# --------------------------------------------------

# Fortin:
# Fortin et al. (2026) developed a global dataset of mean farm size at the first administrative level (ADM1) 
# to capture subnational variation in agricultural structure. The dataset comprises approximately 
# 20,000 administrative units across 200 countries and territories, drawing on agricultural censuses, 
# farm surveys, and official statistical sources collected between 1960 and 2022. Where available, 
# subnational farm-size data were assembled directly from national statistical sources; otherwise, 
# national averages were used. To facilitate comparisons across space and time, the authors also produced versions 
# calibrated to the reference years 2000, 2010, and 2020 using country-level trends in mean farm size.

# We did not use calibrated estimates. We used the variable YEAR, which is the source year (census)
# and the corresponding farm size.


# Read Fortin data:
fp = '/Users/myliheik/Documents/myPython/sustainableFoodProduction/data/GlobalFarmSize_Dataset_v1.1.0/Output/Dataset/GlobalFarmSizeDataset_Calibrated.shp'
gdfFortin = gpd.read_file(fp)

# Surprisingly, these 4 regions in Finland are missing value:
# gdfFortin[(gdfFortin['ISO3'] == 'FIN') & (gdfFortin['FARMSIZE'].isna())]
# "PohjoisSuomi - Lappi", "PohjoisSuomi - PohjoisPohjanmaa", "PohjoisSuomi - KeskiPohjanmaa"
# Perhaps due to changes in ADM1 regions (Keski- and Etelä-Pohjanmaa joined to Pohjanmaa)
# We manually check the farm size from Luke Agricultural statistics (The average farm size in 2010)
# https://statdb.luke.fi/PxWeb/pxweb/fi/LUKE/LUKE__08a%20CAP-indikaattorit__03%20Tuotannon%20kilpailukyky__03%20Maatilan%20keskikoko/01_Maatilan_keskikoko.px/table/tableViewLayout2/?loadedQueryId=da2b7017-6285-4472-be84-aeeb4417a85d&timeType=top&timeValue=14

# mapping for missing FARMSIZE values
fill_finland = {
    "PohjoisSuomi - Lappi": 28,
    "PohjoisSuomi - PohjoisPohjanmaa": 45,
    "PohjoisSuomi - KeskiPohjanmaa": 36, # this is included in Fortin
}


gdfFortin[(gdfFortin['ISO3'] == 'FIN')][['YEAR', 'FARMSIZE']]
region_names = list(fill_finland.keys())
subset = (gdfFortin["ISO3"] == "FIN") & (gdfFortin["NAME_SHP"].isin(region_names))
# fill YEAR only where missing
gdfFortin.loc[subset & gdfFortin["YEAR"].isna(), "YEAR"] = 2010
# fill FARMSIZE only where missing, based on NAME_SHP mapping
gdfFortin.loc[subset & gdfFortin["FARMSIZE"].isna(), "FARMSIZE"] = (
    gdfFortin.loc[subset & gdfFortin["FARMSIZE"].isna(), "NAME_SHP"].map(fill_finland)
)



gdfFortinSince1988 = gdfFortin[gdfFortin['YEAR'] > 1987.0].copy()

gdfFortinSince1988 = gdfFortinSince1988.assign(ADM1_KEY = gdfFortinSince1988["ISO3"] + "_" + gdfFortinSince1988["NAME_SHP"])
# Replace: South-eastern Asia -> South-Eastern Asia
gdfFortinSince1988["SUBSUBREG"] = gdfFortinSince1988["SUBSUBREG"].replace({"South-eastern Asia": "South-Eastern Asia"})
gdfFortinSince1988mini = gdfFortinSince1988[['ISO3', 'YEAR', 'FARMSIZE', 'ADM1_KEY']]

# unique regions == len(gdfFortinSince1988)
gdfFortinSince1988['ADM1_KEY'].nunique(), len(gdfFortinSince1988)
print(f'{gdfFortinSince1988['ADM1_KEY'].nunique()} regions included in Fortin.')
print(f'out of which {len(gdfFortinSince1988[gdfFortinSince1988['FARMSIZE'].isna()])} regions do not have FARMSIZE in Fortin (since 1987).')



# --------------------------------------------------
# Estimate farm size time series at ADM1 level
# --------------------------------------------------

regional_estimates, unmatched_regions = estimate_regions(country_series, subsubregion_series, countrySUBSUBREGdict, gdfFortinSince1988mini,  START_YEAR,   END_YEAR)


# Join geometries for plotting:

regional_estimates_wide = (
    regional_estimates.pivot_table(
        index="ADM1_KEY",
        columns="YEAR",
        values="FARMSIZE_EST"
    )
    .rename_axis(columns=None)
    .reset_index()
)


gdfRegionalEstimates = gdfFortinSince1988.drop(['YEAR', 'FARMSIZE', 'CALIB2000', 'CALIB2010', 'CALIB2020', 'DEF'], axis = 1).merge(regional_estimates_wide, on = 'ADM1_KEY')
print(f'There are {gdfRegionalEstimates['ISO3'].nunique()} countries in filled Fortin.')

# --------------------------------------------------
# ## Diagnostics of the missing countries:

# Check for missing countries (LINEQ vs. Fortin)
countries_in_fortin = gdfFortinSince1988mini["ISO3"].unique()
countries_in_series = country_series.index

missing_countries = set(countries_in_fortin) - set(countries_in_series)

if missing_countries:
    print(f"WARNING: {len(missing_countries)} countries in Fortin are NOT in LINEQ:")
else:
    print(f"All {len(countries_in_fortin)} countries found in country_series")




# ISO3 present in regional dataset
iso_regional = set(gdfFortinSince1988mini["ISO3"].dropna().astype(str).str.strip().str.upper())

# ISO3 present in country series
# (if country_series is indexed by ISO3 as in your code)
iso_country = set(country_series.index.astype(str).str.strip().str.upper())

# found in both
iso_both = sorted(iso_regional & iso_country)

# optional diagnostics
iso_only_regional = sorted(iso_regional - iso_country)
iso_only_country = sorted(iso_country - iso_regional)

{
    "In both": len(iso_both),
    #"both": iso_both,
    "Only in Fortin regional": len(iso_only_regional),
    "Only in LINEQ country": iso_only_country,
}
# COG = Republic of the Congo
# ZMB = Zambia
# We can use trend in Zambia for Angola, i.e. 'Middle Africa'


print('So we are missing trend information for 76 countries. For those we used subsubregional average trend.')
if unmatched_regions['ISO3'].nunique() == 0:
    print('We found subsubregion for all countries.')
else:
    print(f'But for {unmatched_regions['ISO3'].nunique()} we did not find even subsubregion, they are saved in unmatched_regions.\nNext' 
      f' we will search the neighbouring country/region to use as a proxy for these cases.')




# Let's set Uzbekistan -> Eastern Europe
# Let's set Kazakhstan -> Eastern Europe
# Let's set Tajikistan -> Southern Asia
# Let's set Kyrgyzstan -> Southern Asia
# Done above


# ----------------------------------------------------
# Nearest neighbour for the rest of missing regions
# ----------------------------------------------------



"""
So now we have solved all the Fortin countries, we have used trends from WCA census rounds 
either at county or SUBSUBREG level to fill missing years in Fortin data (1992-2020).

But we still have a) countries (several regions) without any Fortin data; 
b) regions of missing data within Fortin countries -> these are ok (supposedly no meaningful agricultural land
e.g. < 2000ha like in Finland is the threshold)


We need to fill the missing NA regions.
The key idea is that missing regions inherit their annual farm-size time series 
from the most geographically appropriate existing region(s), with preference given 
to donors from the same country.

This is our full time series data so far: gdfRegionalEstimates

We will fill every region in missing_gdf (regions with no farm-size estimates) using information 
from regionalEstimates (regions that already have complete annual estimates for 1992–2020).


Which regions are missing?

"""


regionalEstimates = gdfRegionalEstimates.copy()



# Countries in GAUL but missing from regionalEstimates:
missing_in_fortin = sorted(set(gaul['iso3_code']) - set(regionalEstimates['ISO3']))
# Let's leave disputed regions out (starting with x)
# and SJM (Svalbard and Jan Mayen Islands) and 
# ATA (Antarctica):
missing_in_fortin_without_disputed = [item for item in missing_in_fortin if not str(item).startswith("x") and item not in {"ATA", "SJM"}]

print(f'{len(missing_in_fortin_without_disputed)}/{len(missing_in_fortin)} missing if disputed countries/regions (+ SJM and ATA) left out.')



missing_adm0_adm1 = gaul[gaul['iso3_code'].isin(missing_in_fortin_without_disputed)]
print(f'{len(missing_adm0_adm1)} regions (ADM1) missing from our Fortin.')


# mapping missing_regions to SUBSUBREG:
missing_adm0_adm1 = missing_adm0_adm1.assign(SUBSUBREG = missing_adm0_adm1['iso3_code'].map(countrySUBSUBREGdict))
# to fill NaN values in SUBSUBREG with the continent value:
#missing_adm0_adm1['SUBSUBREG'] = missing_adm0_adm1['SUBSUBREG'].fillna(missing_adm0_adm1['continent'])
# These are actually all far away islands or otherwise really small areas (Gibraltar), 
# let's leave them out:
print(f'{len(missing_adm0_adm1[missing_adm0_adm1['SUBSUBREG'].isna()])} small islands or areas without SUBSUBREG information left out')
missing_adm0_adm1 = missing_adm0_adm1[~missing_adm0_adm1['SUBSUBREG'].isna()]
missing_adm0_adm1 = missing_adm0_adm1.assign(ISO3 = missing_adm0_adm1['iso3_code'])



# ------------------------------------------------------------------------
# Fill missing regions using nearest/touching donors from existing regions
# ------------------------------------------------------------------------

missing_regions_filled = fill_missing_regions(missing_adm0_adm1, regionalEstimates, group_col="ISO3", region_col="SUBSUBREG",   year_cols=None,  use_touching=True)



# Missing regions to projection 4326:
missing_regions_filled4326 = missing_regions_filled[~missing_regions_filled[2011].isna()].to_crs(regionalEstimates.crs)
# Build ADM1_KEY identifier for missing regions as well:
missing_regions_filled4326 = missing_regions_filled4326.assign(ADM1_KEY = missing_regions_filled4326["ISO3"] + "_" + missing_regions_filled4326["gaul2_code"].astype(str))

# --------------------------------------------------
# combine missing regions to regionalEstimates
# --------------------------------------------------

common_cols = regionalEstimates.columns.intersection(missing_regions_filled4326.columns)

combined = pd.concat(
    [regionalEstimates[common_cols], missing_regions_filled4326[common_cols]],
    ignore_index=True
)

# --------------------------------------------------
## Save in vector format
# --------------------------------------------------

# Save to output file:
outfile = '/Users/myliheik/Documents/myPython/sustainableFoodProduction/data/extrapolated_farmSize_by_ADM1_from_Fortin2026/extrapolated_farmsize_by_ADM1_from_Fortin_1992_2020.gpkg'

# Convert year column names to strings before saving:
combined_save = combined.copy()
combined_save.columns = [str(c) for c in combined_save.columns]

combined_save.to_file(outfile, driver="GPKG")


# --------------------------------------------------
## Rasterize
# --------------------------------------------------

# GeoDataFrame with polygons + year columns
gdf = combined.copy()

# years you want as raster layers
# year_cols (1992-2020)
year_cols = list(range(1992, 2021))

# grid definition: 5 arc-min global
nrows = int(180 * 60 / 5)   # 2160
ncols = int(360 * 60 / 5)   # 4320
bounds = (-180, -90, 180, 90)  # west, south, east, north

# output file
out_tif = '/Users/myliheik/Documents/myPython/sustainableFoodProduction/data/extrapolated_farmSize_by_ADM1_from_Fortin2026/farmsize_1992_2020_5arcmin.tif'

# nodata + dtype
nodata_val = -9999.0
dtype_out = "float32"

# --------------------------------------------------
# Prepare geometry + CRS
# --------------------------------------------------

gdf = gdf.to_crs("EPSG:4326")
transform = from_bounds(*bounds, width=ncols, height=nrows)

# keep only valid geometries
gdf = gdf.loc[gdf.geometry.notna()].copy()

# --------------------------------------------------
# Write multiband raster
# --------------------------------------------------

with rasterio.open(
    out_tif,
    "w",
    driver="GTiff",
    height=nrows,
    width=ncols,
    count=len(year_cols),
    dtype=dtype_out,
    crs="EPSG:4326",
    transform=transform,
    nodata=nodata_val,
    compress="deflate"
) as dst:

    for band_idx, yr in enumerate(year_cols, start=1):
        if yr not in gdf.columns:
            arr = np.full((nrows, ncols), nodata_val, dtype=np.float32)
            dst.write(arr, band_idx)
            dst.set_band_description(band_idx, str(yr))
            continue

        vals = pd.to_numeric(gdf[yr], errors="coerce")

        # rasterize only polygons with non-missing value for this year
        mask = vals.notna()
        shapes = (
            (geom, float(val))
            for geom, val in zip(gdf.loc[mask, "geometry"], vals.loc[mask])
        )

        arr = rasterize(
            shapes=shapes,
            out_shape=(nrows, ncols),
            transform=transform,
            fill=nodata_val,
            dtype=np.float32,
            all_touched=False
        )

        dst.write(arr, band_idx)
        dst.set_band_description(band_idx, str(yr))


#print(f'Minimum farm size: {combined[year_cols].min().min()}, maximum: {combined[year_cols].max().max()}\n')
idx_per_year = combined[year_cols].apply(pd.to_numeric, errors="coerce").idxmax()
rows_per_year = {yr: combined.loc[[idx]] for yr, idx in idx_per_year.items()}

for i in year_cols:
    maxregion = rows_per_year[i]['ADM1_KEY']
print(f'Maximum farm size between {int(combined[year_cols].max().min())} and {int(combined[year_cols].max().max())} ha in {maxregion.unique()}')

idx_per_year = combined[year_cols].apply(pd.to_numeric, errors="coerce").idxmin()
rows_per_year2 = {yr: combined.loc[[idx]] for yr, idx in idx_per_year.items()}

for i in year_cols:
    minregion = rows_per_year2[i]['ADM1_KEY']
print(f'Minimum farm size between {round(combined[year_cols].min().min(), 5)} and {round(combined[year_cols].min().max(), 5)} ha in {minregion.unique()}\n')


