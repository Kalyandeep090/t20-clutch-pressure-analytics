import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ==========================================
# 1. LOAD & MERGE DATA
# ==========================================
print("Loading datasets...")
balls = pd.read_csv("ball_by_ball.csv")
matches = pd.read_csv("matches.csv")
comps = pd.read_csv("competitions.csv")

df = balls.merge(
    matches[[
        "match_id",
        "comp_id",
        "stage",
        "knock_out",
        "first_inn_revised_overs",
        "second_inn_revised_overs",
        "revised_target",
    ]],
    on="match_id",
    how="left",
)
df = df.merge(comps[["comp_id", "comp_name", "season"]], on="comp_id", how="left")

# Filter to standard 1st & 2nd innings (exclude Super Overs if innings > 2)
df = df[df["innings"].isin([1, 2])].copy()

# Sort strictly chronologically within each match & innings
df = df.sort_values(
    ["match_id", "innings", "overid", "over_ball_num", "innings_ball_num"]
).reset_index(drop=True)

# ==========================================
# 2. COMPETITION TIER WEIGHTING
# ==========================================
TOP_TEAMS = {
    "India",
    "Australia",
    "England",
    "South Africa",
    "New Zealand",
    "West Indies",
    "Pakistan",
    "Sri Lanka",
    "Afghanistan",
    "Bangladesh",
}


def get_comp_weight(comp_name):
  c = str(comp_name)
  if "IPL" in c:
    return 1.00  # Highest weight: direct IPL auction relevance
  if "Emerging" in c or "Rising Stars" in c or "Qualifiers" in c:
    return 0.40
  # Check if both teams in T20I series title are top-10 full members
  matched = sum(1 for t in TOP_TEAMS if t in c)
  if matched >= 2:
    return 0.80
  elif matched == 1:
    return 0.55
  return 0.40


df["comp_weight"] = df["comp_name"].apply(get_comp_weight)

# ==========================================
# 3. BALL-BY-BALL MATCH STATE RECONSTRUCTION
# ==========================================
print("Reconstructing match state before every delivery...")
df["extras_type_clean"] = df["extras_type"].fillna("none")
df["is_wide"] = df["extras_type_clean"] == "wide"
df["is_noball"] = df["extras_type_clean"] == "Overstep"
df["is_legal_ball"] = (~df["is_wide"]) & (~df["is_noball"])
df["is_batter_ball"] = ~df["is_wide"]

df["total_ball_runs"] = (
    df["runs"].fillna(0)
    + df["extras1_runs"].fillna(0)
    + df["extras_2_runs"].fillna(0)
)
df["is_wicket_clean"] = df["is_wicket"].fillna(0).astype(int)

# Cumulative state BEFORE current ball is bowled
grp = df.groupby(["match_id", "innings"])
df["runs_before"] = grp["total_ball_runs"].cumsum() - df["total_ball_runs"]
df["wkts_before"] = grp["is_wicket_clean"].cumsum() - df["is_wicket_clean"]
df["legal_balls_before"] = (
    grp["is_legal_ball"].cumsum() - df["is_legal_ball"].astype(int)
)

# Max overs per innings (handle DLS / rain-shortened games)
df["max_overs"] = np.where(
    df["innings"] == 1,
    df["first_inn_revised_overs"].fillna(20.0),
    df["second_inn_revised_overs"].fillna(20.0),
)
df["max_overs"] = np.where(df["max_overs"] <= 0, 20.0, df["max_overs"])
df["max_balls"] = (df["max_overs"] * 6).astype(int)
df["balls_remaining"] = np.maximum(
    1, df["max_balls"] - df["legal_balls_before"]
)
df["overs_progressed"] = df["legal_balls_before"] / 6.0

# 1st innings final totals to compute 2nd innings target
inn1_totals = (
    df[df["innings"] == 1]
    .groupby("match_id")["total_ball_runs"]
    .sum()
    .rename("inn1_total")
)
df = df.merge(inn1_totals, on="match_id", how="left")
df["target"] = np.where(
    df["revised_target"].notna() & (df["revised_target"] > 0),
    df["revised_target"],
    df["inn1_total"] + 1,
)

df["runs_needed"] = np.where(
    df["innings"] == 2, np.maximum(0, df["target"] - df["runs_before"]), np.nan
)
df["rrr"] = np.where(
    df["innings"] == 2, (df["runs_needed"] * 6.0) / df["balls_remaining"], np.nan
)
df["crr"] = np.where(
    df["legal_balls_before"] > 0,
    (df["runs_before"] * 6.0) / df["legal_balls_before"],
    8.0,
)

# ==========================================
# 4. BALL PRESSURE INDEX (BPI: 0 to 100)
# ==========================================
print("Computing Ball Pressure Index (BPI)...")

# Component 1: Wicket / Collapse Pressure (0 to 40 pts)
# Early wickets hurt more than late wickets
expected_wkts = (df["legal_balls_before"] / df["max_balls"]) * 5.0
wkt_deficit = np.maximum(0, df["wkts_before"] - expected_wkts)
wkt_pressure = np.clip(wkt_deficit * 12.0 + (df["wkts_before"] >= 5) * 10.0, 0, 40)

# Component 2: Scoring Rate / Chase Pressure (0 to 40 pts)
# In 2nd innings: RRR stress. In 1st innings: below-par scoring rate after over 6
inn2_rate_pressure = np.clip((df["rrr"] - 8.0) * 6.5, 0, 40)
inn1_rate_pressure = np.where(
    df["overs_progressed"] >= 6.0,
    np.clip((8.2 - df["crr"]) * 7.5, 0, 30),
    0.0,
)
rate_pressure = np.where(
    df["innings"] == 2, inn2_rate_pressure, inn1_rate_pressure
)

# Component 3: Late-Innings / Close-Contest Leverage (0 to 20 pts)
late_stage = df["legal_balls_before"] >= (df["max_balls"] - 30)  # Last 5 overs
close_chase = (df["innings"] == 2) & (df["rrr"].between(7.5, 15.0))
leverage_pressure = np.where(
    late_stage & (close_chase | (df["innings"] == 1)),
    20.0,
    np.where(late_stage, 10.0, 0.0),
)

# Component 4: Knockout / Playoff Bonus (+8 pts)
is_ko = (
    df["knock_out"].fillna(0).astype(str).str.lower().isin(["1", "true", "yes"])
)
ko_bonus = np.where(is_ko, 8.0, 0.0)

df["bpi"] = np.clip(
    wkt_pressure + rate_pressure + leverage_pressure + ko_bonus, 0, 100
)

# Exclude dead-rubber garbage time in chases (e.g., needing > 24 RPO with 1 wkt left, or < 0.5 RPO)
dead_chase = (df["innings"] == 2) & ((df["rrr"] > 22.0) | (df["rrr"] < 2.0))
df["is_pressure"] = (df["bpi"] >= 45.0) & (~dead_chase)

pct_pressure = df["is_pressure"].mean() * 100
print(f"Total deliveries: {len(df):,} | High-Pressure deliveries: {pct_pressure:.1f}%")

# ==========================================
# 5. BATTER EVALUATION (BASELINE VS PRESSURE)
# ==========================================
print("Evaluating batters...")
bat_df = df[df["is_batter_ball"]].copy()
bat_df["is_boundary"] = (
    (bat_df["is_four"].fillna(0) == 1) | (bat_df["is_six"].fillna(0) == 1)
).astype(int)
bat_df["is_dot"] = (bat_df["runs"].fillna(0) == 0).astype(int)
bat_df["batter_out"] = (
    bat_df["dismissed_player_id"] == bat_df["striker_id"]
).astype(int)

# Weighted ball value per delivery: rewards runs, boundaries, penalizes dots & wickets
bat_df["ball_impact"] = (
    bat_df["runs"].fillna(0) * 1.0
    + bat_df["is_boundary"] * 0.35
    - bat_df["is_dot"] * 0.25
    - bat_df["batter_out"] * 3.5
)


def summarize_batters(sub_df, prefix):
  g = (
      sub_df.groupby(["striker_id", "striker_name"])
      .apply(
          lambda x: pd.Series({
              f"{prefix}_balls": len(x),
              f"{prefix}_innings": x["match_id"].nunique(),
              f"{prefix}_runs": x["runs"].sum(),
              f"{prefix}_outs": x["batter_out"].sum(),
              f"{prefix}_sr": (x["runs"].sum() / len(x)) * 100.0,
              f"{prefix}_bndry_pct": x["is_boundary"].mean() * 100.0,
              f"{prefix}_dot_pct": x["is_dot"].mean() * 100.0,
              f"{prefix}_w_impact": np.average(
                  x["ball_impact"], weights=x["comp_weight"]
              ),
          }),
          include_groups=False,
      )
      .reset_index()
  )
  return g


bat_norm = summarize_batters(bat_df[~bat_df["is_pressure"]], "norm")
bat_pres = summarize_batters(bat_df[bat_df["is_pressure"]], "pres")

# Match-level consistency in pressure innings (min 6 balls faced in pressure in a match)
bat_match_pres = (
    bat_df[bat_df["is_pressure"]]
    .groupby(["striker_id", "match_id"])
    .agg(m_balls=("runs", "count"), m_impact=("ball_impact", "mean"))
    .reset_index()
)
bat_match_pres = bat_match_pres[bat_match_pres["m_balls"] >= 6]
bat_cons = (
    bat_match_pres.groupby("striker_id")["m_impact"]
    .std()
    .fillna(0.5)
    .rename("pres_std")
    .reset_index()
)

bat = bat_pres.merge(bat_norm, on=["striker_id", "striker_name"], how="inner")
bat = bat.merge(bat_cons, on="striker_id", how="left")

# Eligibility filter: >= 150 pressure balls across >= 12 matches, and >= 150 normal balls
bat = bat[
    (bat["pres_balls"] >= 150)
    & (bat["pres_innings"] >= 12)
    & (bat["norm_balls"] >= 150)
].copy()

bat["pres_avg"] = bat["pres_runs"] / np.maximum(1, bat["pres_outs"])
bat["norm_avg"] = bat["norm_runs"] / np.maximum(1, bat["norm_outs"])
bat["sr_delta"] = bat["pres_sr"] - bat["norm_sr"]
bat["impact_delta"] = bat["pres_w_impact"] - bat["norm_w_impact"]

# Empirical Bayes shrinkage toward global pressure impact mean
C_BAT = 120.0
global_bat_mean = bat["pres_w_impact"].mean()
bat["shrunk_pres_impact"] = (
    bat["pres_balls"] * bat["pres_w_impact"] + C_BAT * global_bat_mean
) / (bat["pres_balls"] + C_BAT)

# Composite Clutch Rating (0-100 scale):
# 60% Shrunk Absolute Pressure Impact + 25% Clutch Lift over Own Baseline + 15% Consistency
z_abs = (bat["shrunk_pres_impact"] - bat["shrunk_pres_impact"].mean()) / bat[
    "shrunk_pres_impact"
].std()
z_lift = (bat["impact_delta"] - bat["impact_delta"].mean()) / bat[
    "impact_delta"
].std()
z_cons = -(bat["pres_std"] - bat["pres_std"].mean()) / bat["pres_std"].std()

bat["raw_score"] = 0.60 * z_abs + 0.25 * z_lift + 0.15 * z_cons
bat["clutch_rating"] = 50 + 15 * bat["raw_score"]
bat = bat.sort_values("clutch_rating", ascending=False).reset_index(drop=True)
bat["Rank"] = bat.index + 1

# ==========================================
# 6. BOWLER EVALUATION (BASELINE VS PRESSURE)
# ==========================================
print("Evaluating bowlers...")
BOWLER_DISMISSALS = {"Bowled", "Caught", "Stump", "LBW", "Hit Wicket"}
bowl_df = df.copy()
bowl_df["bowler_runs"] = (
    bowl_df["runs"].fillna(0)
    + np.where(
        bowl_df["extras_type_clean"].isin(["wide", "Overstep"]),
        bowl_df["extras1_runs"].fillna(0) + bowl_df["extras_2_runs"].fillna(0),
        0,
    )
)
bowl_df["bowler_wkt"] = (
    (bowl_df["is_wicket_clean"] == 1)
    & (bowl_df["dismissal_type"].isin(BOWLER_DISMISSALS))
).astype(int)
bowl_df["is_dot_bowl"] = (
    (bowl_df["bowler_runs"] == 0) & (bowl_df["is_legal_ball"])
).astype(int)
bowl_df["is_bndry_conceded"] = (
    (bowl_df["is_four"].fillna(0) == 1) | (bowl_df["is_six"].fillna(0) == 1)
).astype(int)

# Bowler ball impact: rewards dots & wickets, penalizes runs & boundaries
bowl_df["bowl_impact"] = (
    1.25
    - bowl_df["bowler_runs"] * 0.95
    + bowl_df["bowler_wkt"] * 4.2
    + bowl_df["is_dot_bowl"] * 0.35
    - bowl_df["is_bndry_conceded"] * 0.40
)


def summarize_bowlers(sub_df, prefix):
  g = (
      sub_df.groupby(["bowler_id", "bowler_name"])
      .apply(
          lambda x: pd.Series({
              f"{prefix}_balls": x["is_legal_ball"].sum(),
              f"{prefix}_matches": x["match_id"].nunique(),
              f"{prefix}_runs": x["bowler_runs"].sum(),
              f"{prefix}_wkts": x["bowler_wkt"].sum(),
              f"{prefix}_econ": (
                  x["bowler_runs"].sum()
                  / np.maximum(1, x["is_legal_ball"].sum())
              )
              * 6.0,
              f"{prefix}_dot_pct": (
                  x["is_dot_bowl"].sum()
                  / np.maximum(1, x["is_legal_ball"].sum())
              )
              * 100.0,
              f"{prefix}_w_impact": np.average(
                  x["bowl_impact"], weights=x["comp_weight"]
              ),
          }),
          include_groups=False,
      )
      .reset_index()
  )
  return g


bowl_norm = summarize_bowlers(bowl_df[~bowl_df["is_pressure"]], "norm")
bowl_pres = summarize_bowlers(bowl_df[bowl_df["is_pressure"]], "pres")

bowl_match_pres = (
    bowl_df[bowl_df["is_pressure"]]
    .groupby(["bowler_id", "match_id"])
    .agg(m_balls=("is_legal_ball", "sum"), m_impact=("bowl_impact", "mean"))
    .reset_index()
)
bowl_match_pres = bowl_match_pres[bowl_match_pres["m_balls"] >= 6]
bowl_cons = (
    bowl_match_pres.groupby("bowler_id")["m_impact"]
    .std()
    .fillna(0.5)
    .rename("pres_std")
    .reset_index()
)

bowl = bowl_pres.merge(bowl_norm, on=["bowler_id", "bowler_name"], how="inner")
bowl = bowl.merge(bowl_cons, on="bowler_id", how="left")

# Eligibility filter: >= 180 pressure legal balls (30 overs) across >= 15 matches, and >= 180 normal balls
bowl = bowl[
    (bowl["pres_balls"] >= 180)
    & (bowl["pres_matches"] >= 15)
    & (bowl["norm_balls"] >= 180)
].copy()

bowl["econ_delta"] = (
    bowl["norm_econ"] - bowl["pres_econ"]
)  # Positive = tighter economy under pressure
bowl["impact_delta"] = bowl["pres_w_impact"] - bowl["norm_w_impact"]

C_BOWL = 150.0
global_bowl_mean = bowl["pres_w_impact"].mean()
bowl["shrunk_pres_impact"] = (
    bowl["pres_balls"] * bowl["pres_w_impact"] + C_BOWL * global_bowl_mean
) / (bowl["pres_balls"] + C_BOWL)

bz_abs = (bowl["shrunk_pres_impact"] - bowl["shrunk_pres_impact"].mean()) / bowl[
    "shrunk_pres_impact"
].std()
bz_lift = (bowl["impact_delta"] - bowl["impact_delta"].mean()) / bowl[
    "impact_delta"
].std()
bz_cons = -(bowl["pres_std"] - bowl["pres_std"].mean()) / bowl["pres_std"].std()

bowl["raw_score"] = 0.60 * bz_abs + 0.25 * bz_lift + 0.15 * bz_cons
bowl["clutch_rating"] = 50 + 15 * bowl["raw_score"]
bowl = bowl.sort_values("clutch_rating", ascending=False).reset_index(drop=True)
bowl["Rank"] = bowl.index + 1

# ==========================================
# 7. EXPORT TABLES & CHARTS FOR REPORT
# ==========================================
top10_bat = bat.head(10)[
    [
        "Rank",
        "striker_name",
        "pres_balls",
        "pres_innings",
        "norm_sr",
        "pres_sr",
        "sr_delta",
        "pres_avg",
        "pres_dot_pct",
        "clutch_rating",
    ]
]
top10_bowl = bowl.head(10)[
    [
        "Rank",
        "bowler_name",
        "pres_balls",
        "pres_matches",
        "norm_econ",
        "pres_econ",
        "econ_delta",
        "pres_wkts",
        "pres_dot_pct",
        "clutch_rating",
    ]
]

print("\n================ TOP 10 BATTERS UNDER PRESSURE ================")
print(top10_bat.to_string(index=False))

print("\n================ TOP 10 BOWLERS UNDER PRESSURE ================")
print(top10_bowl.to_string(index=False))

top10_bat.to_csv("top10_batters.csv", index=False)
top10_bowl.to_csv("top10_bowlers.csv", index=False)
bat.to_csv("all_batters_ranked.csv", index=False)
bowl.to_csv("all_bowlers_ranked.csv", index=False)

# --- Chart 1: Top 10 Batters Clutch Rating ---
plt.figure(figsize=(10, 5.5))
b_plot = top10_bat.iloc[::-1]
plt.barh(b_plot["striker_name"], b_plot["clutch_rating"], color="#E63946")
plt.xlabel("Composite Clutch Rating (Baseline-Adjusted)")
plt.title("Top 10 Most Reliable Batters Under Pressure (2022–2026 IPL & T20Is)")
for idx, val in enumerate(b_plot["clutch_rating"]):
  plt.text(val + 0.3, idx, f"{val:.1f}", va="center", fontweight="bold")
plt.xlim(0, top10_bat["clutch_rating"].max() + 8)
plt.tight_layout()
plt.savefig("chart1_top10_batters.png", dpi=300)
plt.close()

# --- Chart 2: Top 10 Bowlers Clutch Rating ---
plt.figure(figsize=(10, 5.5))
w_plot = top10_bowl.iloc[::-1]
plt.barh(w_plot["bowler_name"], w_plot["clutch_rating"], color="#1D3557")
plt.xlabel("Composite Clutch Rating (Baseline-Adjusted)")
plt.title("Top 10 Most Reliable Bowlers Under Pressure (2022–2026 IPL & T20Is)")
for idx, val in enumerate(w_plot["clutch_rating"]):
  plt.text(val + 0.3, idx, f"{val:.1f}", va="center", fontweight="bold")
plt.xlim(0, top10_bowl["clutch_rating"].max() + 8)
plt.tight_layout()
plt.savefig("chart2_top10_bowlers.png", dpi=300)
plt.close()

# --- Chart 3: Batter Baseline SR vs Pressure SR ---
plt.figure(figsize=(9, 6))
plt.scatter(
    bat["norm_sr"], bat["pres_sr"], alpha=0.35, color="gray", label="Eligible Batters"
)
plt.scatter(
    top10_bat["norm_sr"],
    top10_bat["pres_sr"],
    color="#E63946",
    s=90,
    zorder=5,
    label="Top 10 Clutch Batters",
)
lims = [100, 195]
plt.plot(lims, lims, "--", color="black", alpha=0.6, label="Parity Line (Pressure SR = Normal SR)")
for _, row in top10_bat.iterrows():
  plt.annotate(
      row["striker_name"],
      (row["norm_sr"] + 0.8, row["pres_sr"] + 0.8),
      fontsize=8.5,
      fontweight="bold",
  )
plt.xlabel("Normal Situations Strike Rate")
plt.ylabel("High-Pressure Situations Strike Rate")
plt.title("Batter Performance Shift: Normal vs. High-Pressure Strike Rate")
plt.legend()
plt.tight_layout()
plt.savefig("chart3_batter_baseline_vs_pressure.png", dpi=300)
plt.close()

# --- Chart 4: Bowler Baseline Economy vs Pressure Economy ---
plt.figure(figsize=(9, 6))
plt.scatter(
    bowl["norm_econ"],
    bowl["pres_econ"],
    alpha=0.35,
    color="gray",
    label="Eligible Bowlers",
)
plt.scatter(
    top10_bowl["norm_econ"],
    top10_bowl["pres_econ"],
    color="#1D3557",
    s=90,
    zorder=5,
    label="Top 10 Clutch Bowlers",
)
elims = [5.5, 11.5]
plt.plot(
    elims,
    elims,
    "--",
    color="black",
    alpha=0.6,
    label="Parity Line (Pressure Econ = Normal Econ)",
)
for _, row in top10_bowl.iterrows():
  plt.annotate(
      row["bowler_name"],
      (row["norm_econ"] + 0.05, row["pres_econ"] + 0.05),
      fontsize=8.5,
      fontweight="bold",
  )
plt.xlabel("Normal Situations Economy Rate")
plt.ylabel("High-Pressure Situations Economy Rate")
plt.title("Bowler Performance Shift: Normal vs. High-Pressure Economy (Lower is Better)")
plt.legend()
plt.tight_layout()
plt.savefig("chart4_bowler_baseline_vs_pressure.png", dpi=300)
plt.close()

print("\nDone! Saved top10_batters.csv, top10_bowlers.csv, and 4 PNG charts.")