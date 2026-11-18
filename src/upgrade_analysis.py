import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Re-run quick validation & rank inspection on saved/raw data
bat = pd.read_csv("all_batters_ranked.csv")
bowl = pd.read_csv("all_bowlers_ranked.csv")

print("=== RANKS 11 TO 25 BATTERS (TO IDENTIFY UNRETAINED AUCTION GEMS) ===")
print(
    bat.iloc[10:25][[
        "Rank",
        "striker_name",
        "pres_balls",
        "norm_sr",
        "pres_sr",
        "sr_delta",
        "pres_avg",
        "clutch_rating",
    ]].to_string(index=False)
)

print("\n=== RANKS 11 TO 25 BOWLERS (TO IDENTIFY UNRETAINED AUCTION GEMS) ===")
print(
    bowl.iloc[10:25][[
        "Rank",
        "bowler_name",
        "pres_balls",
        "norm_econ",
        "pres_econ",
        "econ_delta",
        "pres_wkts",
        "clutch_rating",
    ]].to_string(index=False)
)

# Verify Pressure vs Normal difficulty across dataset & sensitivity
balls = pd.read_csv("ball_by_ball.csv")
matches = pd.read_csv("matches.csv")
df = balls.merge(
    matches[[
        "match_id",
        "knock_out",
        "first_inn_revised_overs",
        "second_inn_revised_overs",
        "revised_target",
    ]],
    on="match_id",
    how="left",
)
df = (
    df[df["innings"].isin([1, 2])]
    .sort_values(
        ["match_id", "innings", "overid", "over_ball_num", "innings_ball_num"]
    )
    .reset_index(drop=True)
)

df["extras_type_clean"] = df["extras_type"].fillna("none")
df["is_wide"] = df["extras_type_clean"] == "wide"
df["is_noball"] = df["extras_type_clean"] == "Overstep"
df["is_legal_ball"] = (~df["is_wide"]) & (~df["is_noball"])
df["total_ball_runs"] = (
    df["runs"].fillna(0)
    + df["extras1_runs"].fillna(0)
    + df["extras_2_runs"].fillna(0)
)
df["is_wicket_clean"] = df["is_wicket"].fillna(0).astype(int)

grp = df.groupby(["match_id", "innings"])
df["runs_before"] = grp["total_ball_runs"].cumsum() - df["total_ball_runs"]
df["wkts_before"] = grp["is_wicket_clean"].cumsum() - df["is_wicket_clean"]
df["legal_balls_before"] = (
    grp["is_legal_ball"].cumsum() - df["is_legal_ball"].astype(int)
)

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

expected_wkts = (df["legal_balls_before"] / df["max_balls"]) * 5.0
wkt_pressure = np.clip(
    np.maximum(0, df["wkts_before"] - expected_wkts) * 12.0
    + (df["wkts_before"] >= 5) * 10.0,
    0,
    40,
)
rate_pressure = np.where(
    df["innings"] == 2,
    np.clip((df["rrr"] - 8.0) * 6.5, 0, 40),
    np.where(
        df["overs_progressed"] >= 6.0,
        np.clip((8.2 - df["crr"]) * 7.5, 0, 30),
        0.0,
    ),
)
late_stage = df["legal_balls_before"] >= (df["max_balls"] - 30)
close_chase = (df["innings"] == 2) & (df["rrr"].between(7.5, 15.0))
leverage_pressure = np.where(
    late_stage & (close_chase | (df["innings"] == 1)),
    20.0,
    np.where(late_stage, 10.0, 0.0),
)
ko_bonus = np.where(
    df["knock_out"].fillna(0).astype(str).str.lower().isin(["1", "true", "yes"]),
    8.0,
    0.0,
)
df["bpi"] = np.clip(
    wkt_pressure + rate_pressure + leverage_pressure + ko_bonus, 0, 100
)
dead_chase = (df["innings"] == 2) & ((df["rrr"] > 22.0) | (df["rrr"] < 2.0))
df["is_pressure"] = (df["bpi"] >= 45.0) & (~dead_chase)

# Global difficulty validation
for label, sub in [
    ("Normal (BPI < 45)", df[~df["is_pressure"]]),
    ("High Pressure (BPI >= 45)", df[df["is_pressure"]]),
]:
  legal = sub[sub["is_legal_ball"]]
  wkt_rate = (sub["is_wicket_clean"].sum() / len(legal)) * 100
  dot_rate = ((sub["runs"] == 0) & sub["is_legal_ball"]).sum() / len(legal) * 100
  print(
      f"\n{label}: {len(sub):,} balls | Wicket Rate: {wkt_rate:.2f}% per ball | Dot Rate: {dot_rate:.1f}%"
  )

# Plot BPI Validation Chart
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0))
ax1.hist(
    df["bpi"],
    bins=25,
    color="#94A3B8",
    edgecolor="white",
    label="Normal (<45)",
)
ax1.hist(
    df[df["is_pressure"]]["bpi"],
    bins=15,
    color="#EA1A85",
    edgecolor="white",
    label="High Pressure (>=45)",
)
ax1.axvline(45, color="#004BA0", linestyle="--", linewidth=2, label="Cutoff = 45")
ax1.set_title("Ball Pressure Index (BPI) Distribution", fontweight="bold")
ax1.set_xlabel("BPI Score (0–100)")
ax1.set_ylabel("Number of Deliveries")
ax1.legend(fontsize=8)

# Wicket rate & Dot rate comparison
cats = ["Wicket Rate (%)", "Dot Ball Rate (%)"]
norm_vals = [
    (
        df[~df["is_pressure"]]["is_wicket_clean"].sum()
        / df[~df["is_pressure"]]["is_legal_ball"].sum()
    )
    * 100,
    (
        (df[~df["is_pressure"]]["runs"] == 0)
        & df[~df["is_pressure"]]["is_legal_ball"]
    ).sum()
    / df[~df["is_pressure"]]["is_legal_ball"].sum()
    * 100,
]
pres_vals = [
    (
        df[df["is_pressure"]]["is_wicket_clean"].sum()
        / df[df["is_pressure"]]["is_legal_ball"].sum()
    )
    * 100,
    (
        (df[df["is_pressure"]]["runs"] == 0)
        & df[df["is_pressure"]]["is_legal_ball"]
    ).sum()
    / df[df["is_pressure"]]["is_legal_ball"].sum()
    * 100,
]
x = np.arange(len(cats))
ax2.bar(x - 0.18, norm_vals, 0.35, label="Normal Balls", color="#004BA0")
ax2.bar(x + 0.18, pres_vals, 0.35, label="Pressure Balls", color="#EA1A85")
for i in range(len(cats)):
  ax2.text(
      x[i] - 0.18,
      norm_vals[i] + 0.8,
      f"{norm_vals[i]:.1f}%",
      ha="center",
      fontsize=8.5,
      fontweight="bold",
  )
  ax2.text(
      x[i] + 0.18,
      pres_vals[i] + 0.8,
      f"{pres_vals[i]:.1f}%",
      ha="center",
      fontsize=8.5,
      fontweight="bold",
  )
ax2.set_xticks(x)
ax2.set_xticklabels(cats, fontweight="bold")
ax2.set_ylim(0, max(pres_vals) + 8)
ax2.set_title("Empirical Proof: Pressure Balls Are Harder", fontweight="bold")
ax2.legend(fontsize=8)

plt.tight_layout()
plt.savefig("chart0_bpi_validation.png", dpi=300, bbox_inches="tight")
plt.close()
print("\nSaved chart0_bpi_validation.png!")