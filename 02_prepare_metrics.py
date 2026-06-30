"""
02_prepare_metrics.py
Reads raw_emissions.csv, computes per-capita and per-GDP-dollar metrics,
adds ISO3 codes + lat/lon (for Tableau map / geocoding), and produces
the final analysis-ready dataset(s):

  - processed_emissions_long.csv   (tidy: one row per country-year-sector)
  - country_year_summary.csv       (one row per country-year, all sectors summed)
  - top_polluters_latest.csv       (ranked latest-year summary, for the policy brief)
"""

import pandas as pd

df = pd.read_csv("/home/claude/co2_project/data/raw_emissions.csv")

# ---------------------------------------------------------------
# Per-capita (tCO2/person) and per-GDP (kgCO2 per $ of GDP) metrics
# ---------------------------------------------------------------
df["Emissions_tCO2_per_capita"] = (df["Emissions_MtCO2"] * 1e6) / (df["Population_Millions"] * 1e6)
df["Emissions_kgCO2_per_GDP_USD"] = (df["Emissions_MtCO2"] * 1e9) / (df["GDP_Billion_USD"] * 1e9)

# ISO3 codes + approximate centroid lat/lon for map plotting (Tableau / Plotly)
geo = {
    "China":          ("CHN", 35.0, 105.0),
    "United States":  ("USA", 39.8, -98.6),
    "India":          ("IND", 22.0, 79.0),
    "Russia":         ("RUS", 61.5, 105.0),
    "Japan":          ("JPN", 36.2, 138.3),
    "Iran":           ("IRN", 32.4, 53.7),
    "Germany":        ("DEU", 51.2, 10.5),
    "South Korea":    ("KOR", 36.5, 127.8),
    "Saudi Arabia":   ("SAU", 23.9, 45.1),
    "Indonesia":      ("IDN", -0.8, 113.9),
    "Canada":         ("CAN", 56.1, -106.3),
    "Brazil":         ("BRA", -14.2, -51.9),
    "South Africa":   ("ZAF", -30.6, 22.9),
    "Mexico":         ("MEX", 23.6, -102.5),
    "Australia":      ("AUS", -25.3, 133.8),
    "United Kingdom": ("GBR", 55.4, -3.4),
    "Turkey":         ("TUR", 38.9, 35.2),
    "Italy":          ("ITA", 41.9, 12.6),
    "France":         ("FRA", 46.2, 2.2),
    "Poland":         ("POL", 51.9, 19.1),
}
df["ISO3"] = df["Country"].map(lambda c: geo[c][0])
df["Lat"] = df["Country"].map(lambda c: geo[c][1])
df["Lon"] = df["Country"].map(lambda c: geo[c][2])

df = df[[
    "Country", "ISO3", "Year", "Sector", "Emissions_MtCO2",
    "Population_Millions", "GDP_Billion_USD",
    "Emissions_tCO2_per_capita", "Emissions_kgCO2_per_GDP_USD",
    "Lat", "Lon",
]].sort_values(["Country", "Year", "Sector"])

df.to_csv("/home/claude/co2_project/data/processed_emissions_long.csv", index=False)

# ---------------------------------------------------------------
# Country-year summary (sectors collapsed) for map view / headline metrics
# ---------------------------------------------------------------
summary = (
    df.groupby(["Country", "ISO3", "Year", "Lat", "Lon"], as_index=False)
      .agg(
          Total_Emissions_MtCO2=("Emissions_MtCO2", "sum"),
          Population_Millions=("Population_Millions", "first"),
          GDP_Billion_USD=("GDP_Billion_USD", "first"),
      )
)
summary["Emissions_tCO2_per_capita"] = (summary["Total_Emissions_MtCO2"] * 1e6) / (summary["Population_Millions"] * 1e6)
summary["Emissions_kgCO2_per_GDP_USD"] = (summary["Total_Emissions_MtCO2"] * 1e9) / (summary["GDP_Billion_USD"] * 1e9)
summary = summary.sort_values(["Year", "Total_Emissions_MtCO2"], ascending=[True, False])
summary.to_csv("/home/claude/co2_project/data/country_year_summary.csv", index=False)

# ---------------------------------------------------------------
# Top polluters in the latest year, with YoY and 2015-latest change, for the brief
# ---------------------------------------------------------------
latest_year = df.Year.max()
first_year = df.Year.min()

latest = summary[summary.Year == latest_year].copy()
base = summary[summary.Year == first_year][["Country", "Total_Emissions_MtCO2"]].rename(
    columns={"Total_Emissions_MtCO2": "Emissions_base_year"}
)
latest = latest.merge(base, on="Country")
latest["Pct_change_since_2015"] = (
    (latest["Total_Emissions_MtCO2"] - latest["Emissions_base_year"]) / latest["Emissions_base_year"] * 100
).round(1)
latest["Global_share_pct"] = (latest["Total_Emissions_MtCO2"] / latest["Total_Emissions_MtCO2"].sum() * 100).round(1)
latest = latest.sort_values("Total_Emissions_MtCO2", ascending=False).reset_index(drop=True)
latest.insert(0, "Rank", latest.index + 1)

# sector breakdown share for latest year, pivoted, to attach to the brief table
sector_latest = df[df.Year == latest_year].pivot_table(
    index="Country", columns="Sector", values="Emissions_MtCO2", aggfunc="sum"
).reset_index()
latest = latest.merge(sector_latest, on="Country", how="left")

latest.to_csv("/home/claude/co2_project/data/top_polluters_latest.csv", index=False)

print("Processed long file:", df.shape)
print("Country-year summary:", summary.shape)
print("\nTop 10 polluters", latest_year, "(MtCO2):")
print(latest[["Rank", "Country", "Total_Emissions_MtCO2", "Global_share_pct", "Pct_change_since_2015"]].head(10).to_string(index=False))
