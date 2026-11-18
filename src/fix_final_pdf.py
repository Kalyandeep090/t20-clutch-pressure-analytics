from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd

top_bat = pd.read_csv("top10_batters.csv")
top_bowl = pd.read_csv("top10_bowlers.csv")

RR_PINK, RR_BLUE, DARK_NAVY, SLATE, LIGHT_BG, CARD_BG, BORDER = (
    "#EA1A85",
    "#004BA0",
    "#111827",
    "#374151",
    "#F8FAFC",
    "#FFFFFF",
    "#CBD5E1",
)


def setup_slide(fig, page_num, section_tag, title, subtitle=""):
  fig.patch.set_facecolor(LIGHT_BG)
  ax = fig.add_axes([0, 0, 1, 1])
  ax.set_xlim(0, 100)
  ax.set_ylim(0, 100)
  ax.axis("off")
  ax.add_patch(plt.Rectangle((0, 97.5), 100, 2.5, color=RR_BLUE))
  ax.add_patch(plt.Rectangle((0, 97.5), 32, 2.5, color=RR_PINK))
  ax.text(
      4,
      93.5,
      section_tag.upper(),
      fontsize=9.5,
      fontweight="bold",
      color=RR_PINK,
  )
  ax.text(
      4, 89.2, title, fontsize=18, fontweight="bold", color=DARK_NAVY
  )
  if subtitle:
    ax.text(4, 85.8, subtitle, fontsize=10.5, color=SLATE)
  ax.plot([4, 96], [84.2, 84.2], color=BORDER, linewidth=1.0)
  ax.plot([4, 96], [4.5, 4.5], color=BORDER, linewidth=0.8)
  ax.text(
      4,
      2.2,
      "SupeRR Selector Season 2 | Round 1: Identifying Reliable Players Under Pressure",
      fontsize=8.5,
      color=SLATE,
  )
  ax.text(
      96,
      2.2,
      f"Page {page_num} of 8",
      fontsize=8.5,
      fontweight="bold",
      color=RR_BLUE,
      ha="right",
  )
  return ax


def draw_card(
    ax, x, y, w, h, header, body_lines, accent=RR_BLUE, mono=False, line_gap=3.3
):
  ax.add_patch(
      plt.Rectangle(
          (x, y),
          w,
          h,
          facecolor=CARD_BG,
          edgecolor=BORDER,
          linewidth=1.0,
          zorder=1,
      )
  )
  ax.add_patch(
      plt.Rectangle((x, y + h - 0.8), w, 0.8, facecolor=accent, zorder=2)
  )
  ax.text(
      x + 1.5,
      y + h - 3.3,
      header,
      fontsize=10.8,
      fontweight="bold",
      color=DARK_NAVY,
      zorder=3,
  )
  curr_y = y + h - 6.4
  for line in body_lines:
    ax.text(
        x + 1.5,
        curr_y,
        line,
        fontsize=8.6 if mono else 9.0,
        color=SLATE,
        zorder=3,
        fontfamily="monospace" if mono else "sans-serif",
    )
    curr_y -= line_gap


with PdfPages("SupeRR_Selector_Round1_Final.pdf") as pdf:
  # PAGE 1: EXECUTIVE SUMMARY (Fixed bottom blue box padding)
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      1,
      "Executive Summary",
      "Quantifying Clutch: Reliable Performers Under Pressure",
      "A Delivery-Level Baseline-Adjusted Framework Across IPL & T20Is (2022–2026)",
  )
  kpis = [
      ("200,961", "Total Deliveries Analyzed", RR_BLUE),
      ("16.1% (32,375)", "High-Pressure Balls (+48% Wkt Rate)", RR_PINK),
      ("66.6 Rating", "#1 Batter: David Miller (+26.2 SR)", RR_BLUE),
      ("87.2 Rating", "#1 Bowler: Sufiyan Muqeem (4.76 Econ)", RR_PINK),
  ]
  for i, (val, lbl, col) in enumerate(kpis):
    kx = 4 + i * 23.3
    ax.add_patch(
        plt.Rectangle(
            (kx, 69.5), 22.0, 12.0, facecolor=CARD_BG, edgecolor=BORDER, lw=1
        )
    )
    ax.add_patch(plt.Rectangle((kx, 80.7), 22.0, 0.8, facecolor=col))
    ax.text(
        kx + 1.5, 75.8, val, fontsize=14.5, fontweight="bold", color=col
    )
    ax.text(kx + 1.5, 71.5, lbl, fontsize=8.8, color=SLATE)

  bat_lines = [
      f"#{int(r.Rank):02d} {r.striker_name:<21} | {r.clutch_rating:4.1f} | SR:{r.pres_sr:5.1f}"
      for _, r in top_bat.iterrows()
  ]
  bowl_lines = [
      f"#{int(r.Rank):02d} {r.bowler_name:<21} | {r.clutch_rating:4.1f} | Ec:{r.pres_econ:4.2f}"
      for _, r in top_bowl.iterrows()
  ]
  draw_card(
      ax,
      4,
      20.5,
      44.5,
      46.5,
      "Final Top 10 Batters Under Pressure",
      bat_lines,
      accent=RR_PINK,
      mono=True,
  )
  draw_card(
      ax,
      51.5,
      20.5,
      44.5,
      46.5,
      "Final Top 10 Bowlers Under Pressure",
      bowl_lines,
      accent=RR_BLUE,
      mono=True,
  )

  # Cleanly padded bottom callout banner
  ax.add_patch(
      plt.Rectangle(
          (4, 6.8), 92, 11.2, facecolor="#EFF6FF", edgecolor=RR_BLUE, lw=1.2
      )
  )
  ax.text(
      6,
      15.0,
      "CORE METHODOLOGY INSIGHT:",
      fontsize=9.5,
      fontweight="bold",
      color=RR_BLUE,
  )
  ax.text(
      6,
      11.7,
      "Rather than rewarding raw volume or reputation, our Composite Clutch Rating isolates players who statistically improve upon their",
      fontsize=9.1,
      color=DARK_NAVY,
  )
  ax.text(
      6,
      8.7,
      "own normal baseline during high-leverage game states, validated via Empirical Bayes shrinkage, tier weights, and consistency.",
      fontsize=9.1,
      color=DARK_NAVY,
  )
  pdf.savefig(fig)
  plt.close(fig)

  # PAGE 2: DEFINING PRESSURE + EMPIRICAL VALIDATION CHART
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      2,
      "Step 1: Pressure Definition & Empirical Proof",
      "Ball Pressure Index (BPI): Pre-Delivery Match Context",
      "Pre-ball state reconstruction prevents look-ahead bias and isolates genuinely harder game states",
  )
  draw_card(
      ax,
      4,
      46,
      45,
      36,
      "4-Component BPI Formula (0–100 Scale)",
      [
          "1. Wicket/Collapse Stress (0–40): Actual wickets above expected",
          "   trajectory [(Balls/MaxBalls)×5] × 12 + [Wkts >= 5] × 10.",
          "2. Scoring/Chase Rate (0–40): 2nd Inn RRR > 8.0 [(RRR-8)×6.5];",
          "   1st Inn CRR < 8.2 after Over 6 [(8.2-CRR)×7.5]; DLS-adjusted.",
          "3. Late Leverage (0–20): Final 5 overs in close chases (RRR 7.5–15).",
          "4. Knockout Amplifier (+8): IPL Playoffs, Finals & ICC Knockouts.",
          "• High Pressure Cutoff: BPI >= 45 (excluding dead chases >22/<2 RPO).",
      ],
      accent=RR_PINK,
      line_gap=3.6,
  )

  draw_card(
      ax,
      51,
      46,
      45,
      36,
      "Empirical Validation: Why BPI >= 45 Works",
      [
          "• Across 200,961 deliveries, 32,375 balls (16.1%) exceed BPI 45.",
          "• Wicket Rate Jumps +47.9%: Dismissals rise from 5.24% per legal",
          "  ball in Normal play (BPI < 45) to 7.75% under High Pressure.",
          "• Dot-Ball Squeeze: Dot-ball frequency rises from 36.9% to 38.0%",
          "  even during death-over chases when batters are forced to attack.",
          "• Confirms BPI cleanly separates high-stress inflection points",
          "  from routine low-leverage overs.",
      ],
      accent=RR_BLUE,
      line_gap=3.6,
  )

  ax_img0 = fig.add_axes([0.08, 0.08, 0.84, 0.35])
  ax_img0.imshow(mpimg.imread("chart0_bpi_validation.png"))
  ax_img0.axis("off")
  pdf.savefig(fig)
  plt.close(fig)

  # PAGE 3: SCORING & FAIR COMPARISONS
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      3,
      "Step 2 & 3: Rating Architecture",
      "Baseline Comparison, Sample Shrinkage & Fair Context",
      "Ensuring apples-to-apples comparisons across IPL and T20 International cricket",
  )
  draw_card(
      ax,
      4,
      48,
      44.5,
      33,
      "Delivery-Level Performance Equations",
      [
          "• Batting Ball Impact (excludes wides from balls faced):",
          "  Impact = Runs + 0.35(Boundary) - 0.25(Dot) - 3.50(Batter Out)",
          "• Bowling Ball Impact (excludes wides/no-balls from legal count;",
          "  excludes run-outs & obstructing field from bowler wickets):",
          "  Impact = 1.25 - 0.95(Runs) + 4.20(Wkt) + 0.35(Dot) - 0.40(Bndry)",
          "• Computed separately on Pressure balls vs. Normal balls.",
      ],
      accent=RR_BLUE,
  )
  draw_card(
      ax,
      51.5,
      48,
      44.5,
      33,
      "Competition Tier Weighting (IPL vs. T20Is)",
      [
          "• Prevents stat-padding in Associate/Emerging fixtures:",
          "  - IPL (2022–2026): Weight = 1.00 (Primary benchmark)",
          "  - Top-10 Full-Member T20Is: Weight = 0.80",
          "  - Single Full-Member Bilateral T20Is: Weight = 0.55",
          "  - Associate / Emerging / Rising Stars: Weight = 0.40",
          "• Weighted impact ensures elite opposition quality drives rank.",
      ],
      accent=RR_PINK,
  )
  draw_card(
      ax,
      4,
      10,
      44.5,
      34,
      "Eligibility Cutoffs & Empirical Bayes Shrinkage",
      [
          "• Minimum Sample Gates (Eliminates small-sample flukes):",
          "  - Batters: >= 150 Pressure Balls across >= 12 Innings (+150 Norm)",
          "  - Bowlers: >= 180 Pressure Balls (30 overs) across >= 15 Matches",
          "• Empirical Bayes Shrinkage toward Global Pressure Mean:",
          "  Shrunk Impact = (n × Player_Impact + C × Global_Mean) / (n + C)",
          "  where smoothing constant C = 120 balls (bat) / 150 balls (bowl).",
      ],
      accent=RR_PINK,
  )
  draw_card(
      ax,
      51.5,
      10,
      44.5,
      34,
      "Composite Clutch Rating Formula (50 ± 15 Scale)",
      [
          "• Combines three standardized Z-score pillars:",
          "  1. Absolute Pressure Execution (60%): Shrunk Pressure Impact",
          "  2. Baseline Clutch Lift (25%): Pressure Impact - Normal Impact",
          "  3. Match Consistency (15%): Negative Match-to-Match Std Dev",
          "• Raw Score = 0.60·Z(Shrunk) + 0.25·Z(Lift) + 0.15·Z(Consistency)",
          "• Final Clutch Rating = 50 + 15 × Raw Score.",
      ],
      accent=RR_BLUE,
  )
  pdf.savefig(fig)
  plt.close(fig)

  # PAGE 4: TOP 10 BATTERS TABLE & CHART
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      4,
      "Evidence: Batting Rankings",
      "Top 10 Most Reliable Batters Under Pressure",
      "Ranked by Composite Clutch Rating (Minimum 150 Pressure Balls & 12 Pressure Innings)",
  )
  ax_tbl = fig.add_axes([0.04, 0.12, 0.52, 0.68])
  ax_tbl.axis("off")
  col_labels = [
      "Rank",
      "Batter",
      "Pres\nBalls",
      "Norm\nSR",
      "Pres\nSR",
      "SR\nDelta",
      "Pres\nAvg",
      "Clutch\nRating",
  ]
  table_data = [
      [
          f"#{int(r.Rank)}",
          r.striker_name,
          f"{int(r.pres_balls)}",
          f"{r.norm_sr:.1f}",
          f"{r.pres_sr:.1f}",
          f"+{r.sr_delta:.1f}" if r.sr_delta >= 0 else f"{r.sr_delta:.1f}",
          f"{r.pres_avg:.1f}",
          f"{r.clutch_rating:.1f}",
      ]
      for _, r in top_bat.iterrows()
  ]
  tbl = ax_tbl.table(
      cellText=table_data,
      colLabels=col_labels,
      loc="center",
      cellLoc="center",
      colWidths=[0.08, 0.28, 0.10, 0.10, 0.10, 0.11, 0.10, 0.13],
  )
  tbl.auto_set_font_size(False)
  tbl.set_fontsize(8.8)
  tbl.scale(1, 1.85)
  for (row, col), cell in tbl.get_celld().items():
    cell.set_edgecolor(BORDER)
    if row == 0:
      cell.set_facecolor(RR_BLUE)
      cell.get_text().set_color("white")
      cell.get_text().set_fontweight("bold")
    else:
      cell.set_facecolor("#FFFFFF" if row % 2 == 1 else "#F1F5F9")
      if col == 1:
        cell.get_text().set_ha("left")
        cell.get_text().set_fontweight("bold")
      if col == 7:
        cell.get_text().set_color(RR_PINK)
        cell.get_text().set_fontweight("bold")
  ax_img = fig.add_axes([0.57, 0.13, 0.40, 0.67])
  ax_img.imshow(mpimg.imread("chart1_top10_batters.png"))
  ax_img.axis("off")
  pdf.savefig(fig)
  plt.close(fig)

  # PAGE 5: BATTER BASELINE VS PRESSURE SHIFT
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      5,
      "Evidence: Batting Clutch Lift",
      "Batter Performance Shift: Normal vs. Pressure Strike Rate",
      "Every Top 10 batter accelerates above the parity line when match pressure spikes",
  )
  ax_img = fig.add_axes([0.04, 0.11, 0.56, 0.70])
  ax_img.imshow(mpimg.imread("chart3_batter_baseline_vs_pressure.png"))
  ax_img.axis("off")
  draw_card(
      ax,
      62,
      47,
      34,
      34,
      "Elite Death Finishers Scale Up",
      [
          "• David Miller (#1, 66.6): Lifts SR by +26.2",
          "  (143.6 -> 169.8) across 278 pressure balls",
          "  with a 39.3 average.",
          "• Tristan Stubbs (#2, 66.3): Highest pressure",
          "  volume (344 balls), 63.9 avg, and lowest",
          "  dot-ball rate (24.4%) among all qualifiers.",
      ],
      accent=RR_PINK,
  )
  draw_card(
      ax,
      62,
      10,
      34,
      34,
      "Collapse Anchors & Rotation Control",
      [
          "• Tilak Varma (#3, 65.7): Surges +32.6 SR",
          "  under pressure (171.7 SR, 46.8 avg across",
          "  31 pressure innings).",
          "• Ayush Badoni (#8, 61.7): Averages an",
          "  extraordinary 83.3 under pressure (26.5%",
          "  dots), excelling in middle-order rescues.",
      ],
      accent=RR_BLUE,
  )
  pdf.savefig(fig)
  plt.close(fig)

  # PAGE 6: TOP 10 BOWLERS TABLE & CHART
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      6,
      "Evidence: Bowling Rankings",
      "Top 10 Most Reliable Bowlers Under Pressure",
      "Ranked by Composite Clutch Rating (Minimum 180 Pressure Legal Balls & 15 Matches)",
  )
  ax_tbl = fig.add_axes([0.04, 0.12, 0.52, 0.68])
  ax_tbl.axis("off")
  b_cols = [
      "Rank",
      "Bowler",
      "Pres\nBalls",
      "Norm\nEcon",
      "Pres\nEcon",
      "Econ\nSaved",
      "Pres\nWkts",
      "Clutch\nRating",
  ]
  b_data = [
      [
          f"#{int(r.Rank)}",
          r.bowler_name,
          f"{int(r.pres_balls)}",
          f"{r.norm_econ:.2f}",
          f"{r.pres_econ:.2f}",
          f"+{r.econ_delta:.2f}" if r.econ_delta >= 0 else f"{r.econ_delta:.2f}",
          f"{int(r.pres_wkts)}",
          f"{r.clutch_rating:.1f}",
      ]
      for _, r in top_bowl.iterrows()
  ]
  tbl2 = ax_tbl.table(
      cellText=b_data,
      colLabels=b_cols,
      loc="center",
      cellLoc="center",
      colWidths=[0.08, 0.28, 0.10, 0.10, 0.10, 0.11, 0.10, 0.13],
  )
  tbl2.auto_set_font_size(False)
  tbl2.set_fontsize(8.8)
  tbl2.scale(1, 1.85)
  for (row, col), cell in tbl2.get_celld().items():
    cell.set_edgecolor(BORDER)
    if row == 0:
      cell.set_facecolor(RR_BLUE)
      cell.get_text().set_color("white")
      cell.get_text().set_fontweight("bold")
    else:
      cell.set_facecolor("#FFFFFF" if row % 2 == 1 else "#F1F5F9")
      if col == 1:
        cell.get_text().set_ha("left")
        cell.get_text().set_fontweight("bold")
      if col == 7:
        cell.get_text().set_color(RR_BLUE)
        cell.get_text().set_fontweight("bold")
  ax_img = fig.add_axes([0.57, 0.13, 0.40, 0.67])
  ax_img.imshow(mpimg.imread("chart2_top10_bowlers.png"))
  ax_img.axis("off")
  pdf.savefig(fig)
  plt.close(fig)

  # PAGE 7: BOWLER BASELINE VS PRESSURE SHIFT
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      7,
      "Evidence: Bowling Clutch Lift",
      "Bowler Performance Shift: Normal vs. Pressure Economy",
      "All Top 10 bowlers tighten their economy rate by 0.54 to 2.55 RPO under pressure",
  )
  ax_img = fig.add_axes([0.04, 0.11, 0.56, 0.70])
  ax_img.imshow(mpimg.imread("chart4_bowler_baseline_vs_pressure.png"))
  ax_img.axis("off")
  draw_card(
      ax,
      62,
      47,
      34,
      34,
      "Middle-Over Spin Stranglehold",
      [
          "• Sufiyan Muqeem (#1, 87.2) & Abrar Ahmed",
          "  (#2, 73.1): Sub-4.85 pressure economies",
          "  with >52% dot balls when RRR climbs.",
          "• Sunil Narine (#3, 72.3) & Suyash Sharma",
          "  (#7, 61.7): Suyash cuts economy by 1.75",
          "  RPO under pressure (9.01 -> 7.27).",
      ],
      accent=RR_BLUE,
  )
  draw_card(
      ax,
      62,
      10,
      34,
      34,
      "High-Volume Death Pace Enforcers",
      [
          "• Mustafizur Rahman (#4, 68.5): 30 pressure",
          "  wickets across 359 balls at 6.79 economy.",
          "• Matheesha Pathirana (#5, 67.0): 25 wickets,",
          "  dropping economy from 9.31 to 7.57 in",
          "  high-leverage death overs.",
          "• Jasprit Bumrah (#10, 57.2): 40 pressure games.",
      ],
      accent=RR_PINK,
  )
  pdf.savefig(fig)
  plt.close(fig)

  # PAGE 8: RELIABILITY, SENSITIVITY & LIMITATIONS
  fig = plt.figure(figsize=(13.33, 7.5))
  ax = setup_slide(
      fig,
      8,
      "Reliability & Model Limitations",
      "Consistency Validation, Sensitivity Checks & Known Caveats",
      "Verifying statistical stability across matches and identifying areas of model uncertainty",
  )
  draw_card(
      ax,
      4,
      47,
      44.5,
      34,
      "1. Match-to-Match Consistency Verification",
      [
          "• Variance Penalization (15% Weight): Computing innings-level impact",
          "  standard deviation across games with >= 6 pressure balls prevents",
          "  single-match heroics from masking frequent failures.",
          "• Multi-Season Volume Depth: Top 10 qualifiers average 250+ pressure",
          "  balls across 20–40 matches (e.g., Bumrah 40, Mustafizur 39,",
          "  Tim David 33, Santner 32, Tilak Varma 31, Pathirana 30).",
      ],
      accent=RR_BLUE,
  )
  draw_card(
      ax,
      51.5,
      47,
      44.5,
      34,
      "2. Where the Model Is Less Certain (Limitations)",
      [
          "• Venue & Pitch Par Scores: Fixed RRR baselines (8.0 RPO) treat",
          "  high-scoring venues (Chinnaswamy) identically to slower pitches",
          "  (Chepauk/Ekana) rather than using venue-season par adjustments.",
          "• Series vs. Opponent-Level Elo: Competition weights operate at the",
          "  tournament/series tier rather than ball-by-ball batter-bowler Elo,",
          "  slightly favoring bilateral specialists (e.g., Muqeem, Abrar).",
      ],
      accent=RR_PINK,
  )
  draw_card(
      ax,
      4,
      10,
      92,
      33,
      "3. Methodological Robustness & Scope Alignment",
      [
          "• Pure Dataset Objectivity: In strict alignment with Round 1 guidelines, rankings evaluate all players in the 2022–2026 IPL & T20I",
          "  dataset solely on empirical pressure performance—without distorting scores for franchise retention or retirement status.",
          "• Dead-Rubber & Edge-Case Protection: Excluding chases with RRR > 22.0 or < 2.0 eliminates garbage-time stat-padding, while DLS",
          "  revised-over adjustments ensure rain-shortened matches are scored on true required rates.",
          "• Next-Stage Extensions: Incorporating venue-adjusted Expected Runs (xR) and Win Probability Added (WPA) models provides a direct",
          "  path to Phase 2 match-simulation modeling.",
      ],
      accent=RR_BLUE,
      line_gap=3.5,
  )
  pdf.savefig(fig)
  plt.close(fig)

print("Created SupeRR_Selector_Round1_Final.pdf successfully!")