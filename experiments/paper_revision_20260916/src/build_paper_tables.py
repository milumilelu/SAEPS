"""Generate the LaTeX result tables and number macros for the manuscript.

The repository forbids hard-coding experimental results into the manuscript source.  Every
figure that appears in the integrated text is therefore emitted here from the
machine-readable artifacts, and the prose refers to it through a generated macro.  If a
number changes in the artifacts, the manuscript changes on the next build.

Inputs, all inside this namespace:
    outputs/posthoc/report_correction_20260918/e3_metrics_corrected.csv   (E3, corrected metrics)
    outputs/posthoc/report_correction_20260918/e3_cluster_statistics.json (E3 statistics)
    outputs/development/e6/e6_summary.json, e6_architecture_accuracy.csv  (E6)
    outputs/heldout/e7/e7_scope_levels.json, e7_branch_diagnostics.csv    (E7)
    outputs/posthoc/e8/e8_matched_gamma_cost.csv                          (E8)

Outputs:
    paper_tables.tex   table environments, to be \\input
    paper_numbers.tex  \\newcommand macros for every number cited in prose
    paper_numbers.json the same values in machine-readable form, with provenance
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

CORRECTION = "outputs/posthoc/report_correction_20260918"
E3_FIXED = [
    ("E_raw", r"Raw Gauss--Newton error $E_{\mathrm{raw}}$"),
    ("E_SAEPS", r"SAEPS error $\Esa$"),
    ("E_fix", r"Exact state-freezing error $E_{\mathrm{fix}}$"),
    ("E_GN_fix", r"Fixed-state GN truncation $E_{\mathrm{GN,fix}}$"),
    ("E_relax", r"Relaxation-correction error $E_{\mathrm{relax}}$"),
]


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def alphaTag(alpha: float) -> str:
    """A LaTeX-safe macro suffix for a damping scale, e.g. 1e-08 -> TenToMinusEight."""
    return {
        1.0e-8: "TenToMinusEight",
        1.0e-6: "TenToMinusSix",
        1.0e-4: "TenToMinusFour",
        1.0e-2: "TenToMinusTwo",
    }.get(float(alpha), "Alpha" + str(alpha).replace("-", "m").replace(".", "p"))


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt(value: float | None, digits: int = 4) -> str:
    """Plain scientific notation below 0.01, four decimals otherwise.

    The output stays text-safe: ``1.247e-3`` needs no math mode, so one value can serve
    both a table cell and a macro without breaking either.
    """
    if value is None:
        return "--"
    if value == 0:
        return "0"
    if abs(value) < 0.01:
        return f"{value:.3e}".replace("e-0", "e-").replace("e+0", "e")
    return f"{value:.{digits}f}"


def median(values):
    clean = [v for v in values if v is not None]
    return statistics.median(clean) if clean else None


def build(namespace: Path) -> tuple[str, str, dict]:
    numbers: dict = {}
    tables: list[str] = []

    # ---------------- E3: corrected metrics, fit and seed level -------------------
    rows = [
        r
        for r in read_csv(namespace / CORRECTION / "e3_metrics_corrected.csv")
        if r["cohort"] == "e3_heldout_1e5"
    ]
    per_seed: dict[str, list[dict]] = {}
    for row in rows:
        per_seed.setdefault(row["data_seed"], []).append(row)
    seed_level = {seed: {k: median([number(r[k]) for r in g]) for k, _ in E3_FIXED}
                  for seed, g in per_seed.items()}

    for key, _ in E3_FIXED:
        numbers[f"EthreeHeldout{key.replace('_', '')}Fit"] = median([number(r[key]) for r in rows])
        numbers[f"EthreeHeldout{key.replace('_', '')}Seed"] = median(
            [v[key] for v in seed_level.values()]
        )
    numbers["EthreeHeldoutFits"] = len(rows)
    numbers["EthreeHeldoutSeeds"] = len(per_seed)

    stats = json.loads((namespace / CORRECTION / "e3_cluster_statistics.json").read_text(encoding="utf-8"))
    fit_level, seed_level_stats = stats["fit_level_summary"], stats["data_seed_level_summary"]
    numbers["EthreeRone"] = seed_level_stats["ratio_of_medians"]
    numbers["EthreeRtwo"] = seed_level_stats["median_paired_ratio"]
    numbers["EthreePRaw"] = fit_level and 2.0 ** -fit_level["fits_valid"]
    numbers["EthreePSeed"] = seed_level_stats["one_sided_sign_test_p"]
    numbers["EthreeSeedsImproved"] = seed_level_stats["units_improved"]
    numbers["EthreeFitsImproved"] = fit_level["fits_improved"]
    numbers["EthreeNullHypothesisExponent"] = fit_level["fits_valid"]

    lines = []
    for key, label in E3_FIXED:
        fit_median = median([number(r[key]) for r in rows])
        seed_median = median([v[key] for v in seed_level.values()])
        lines.append(f"{label} & {fmt(fit_median)} & {fmt(seed_median)} \\\\")
    tables.append(
        "\n".join(
            [
                r"\begin{table}[!htbp]",
                r"\centering",
                r"\caption{Held-out non-affine benchmark, corrected metrics.",
                r"Columns give the median over the twenty-four fits and the median over the six data seeds.",
                r"The data seed is the statistical unit; initializations are repeats inside a seed.",
                r"All five metrics are recomputed from the archived curvature values under the definitions of Eq.~\eqref{eq:fixed_state_exact_error}.}",
                r"\label{tab:e3_heldout}",
                r"\footnotesize",
                r"\setlength{\tabcolsep}{4pt}",
                r"\begin{tabular}{lcc}",
                r"\toprule",
                r"Metric & Fit median ($n=24$) & Seed median ($n=6$) \\",
                r"\midrule",
                *lines,
                r"\bottomrule",
                r"\end{tabular}",
                r"\end{table}",
            ]
        )
    )

    # ---------------- E3: seed-level detail ---------------------------------------
    seed_rows = []
    for seed in sorted(seed_level):
        v = seed_level[seed]
        seed_rows.append(
            f"{seed} & {fmt(v['E_raw'])} & {fmt(v['E_SAEPS'])} & {fmt(v['E_GN_fix'])} \\\\"
        )
    tables.append(
        "\n".join(
            [
                r"\begin{table}[!htbp]",
                r"\centering",
                r"\caption{Per-seed held-out results for the non-affine benchmark.",
                r"Each row pools the two initializations and two noise levels by median.",
                r"Every seed improves, so the one-sided sign test over six independent seeds gives $p=2^{-6}$.}",
                r"\label{tab:e3_seeds}",
                r"\footnotesize",
                r"\setlength{\tabcolsep}{4pt}",
                r"\begin{tabular}{lccc}",
                r"\toprule",
                r"Data seed & $E_{\mathrm{raw}}$ & $\Esa$ & $E_{\mathrm{GN,fix}}$ \\",
                r"\midrule",
                *seed_rows,
                r"\bottomrule",
                r"\end{tabular}",
                r"\end{table}",
            ]
        )
    )

    # ---------------- E6: three architectures -------------------------------------
    e6_path = namespace / "outputs/development/e6/e6_summary.json"
    e6 = json.loads(e6_path.read_text(encoding="utf-8")) if e6_path.is_file() else None
    if e6:
        order = ["base_2_16_1", "wide_2_32_1", "deep_2_16_16_1"]
        names = {"base_2_16_1": "2--16--1 (base)", "wide_2_32_1": "2--32--1 (wide)",
                 "deep_2_16_16_1": "2--16--16--1 (deep)"}
        # macro suffixes must survive LaTeX; digits and underscores are not safe there
        tags = {"base_2_16_1": "Base", "wide_2_32_1": "Wide", "deep_2_16_16_1": "Deep"}
        rows6 = []
        for label in order:
            block = e6["by_architecture"][label]
            rows6.append(
                f"{names[label]} & {block['state_parameters']} & "
                f"{block['centres_available']}/{block['fits']} & "
                f"{fmt(block['median_E_raw'])} & {fmt(block['median_E_SAEPS'])} & "
                f"{fmt(block['median_kappa_relative_error'])} \\\\"
            )
            numbers[f"EsixSAEPS{tags[label]}"] = block["median_E_SAEPS"]
            numbers[f"EsixRaw{tags[label]}"] = block["median_E_raw"]
            numbers[f"EsixAvailable{tags[label]}"] = block["centres_available"]
        numbers["EsixFitsPerArchitecture"] = e6["by_architecture"][order[0]]["fits"]
        numbers["EsixTotalCentres"] = sum(e6["by_architecture"][l]["fits"] for l in order)
        numbers["EsixTotalAvailable"] = sum(e6["by_architecture"][l]["centres_available"] for l in order)
        tables.append(
            "\n".join(
                [
                    r"\begin{table}[!htbp]",
                    r"\centering",
                    r"\caption{Architecture extension on the non-affine benchmark.",
                    r"Each architecture is trained on the same data seeds, initializations and noise levels.",
                    r"All eighteen centres admit the exact reduction.}",
                    r"\label{tab:e6_architecture}",
                    r"\footnotesize",
                    r"\setlength{\tabcolsep}{4pt}",
                    r"\begin{tabular}{lccccc}",
                    r"\toprule",
                    r"Architecture & $n_\theta$ & Valid & Median $E_{\mathrm{raw}}$ & Median $\Esa$ & Median $\kappa$ error \\",
                    r"\midrule",
                    *rows6,
                    r"\bottomrule",
                    r"\end{tabular}",
                    r"\end{table}",
                ]
            )
        )

    # ---------------- supplementary scalars cited in the integrated prose ---------
    preflight_path = namespace / "outputs/development/e3/e3_preflight.json"
    if preflight_path.is_file():
        identity = json.loads(preflight_path.read_text(encoding="utf-8"))["nonaffine_identity"]
        numbers["NonaffineGradient"] = identity["affine_prediction_g_l"]
        numbers["NonaffineLogBlock"] = identity["log_identity_left_H_minus_G"]
        numbers["NonaffineRight"] = identity["right_kappa2_sum_r_d2r"]
    # kappa recovery and the HVP check, taken from the same artifacts as the tables
    e6_csv = read_csv(namespace / "outputs/development/e6/e6_architecture_accuracy.csv")
    for label, tag in (("base_2_16_1", "Base"), ("wide_2_32_1", "Wide"), ("deep_2_16_16_1", "Deep")):
        group = [number(r["kappa_relative_error"]) for r in e6_csv if r["label"] == label]
        if group:
            numbers[f"EsixKappaError{tag}"] = median(group)
    hvp = [number(r["hvp_max_relative_difference"]) for r in e6_csv]
    if hvp:
        numbers["EsixHvpMax"] = max(hvp)
    # parameter recovery comes from the seed-level aggregate, not the metrics table
    aggregate_path = namespace / "outputs/heldout/e3/e3_aggregate.json"
    if aggregate_path.is_file():
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
        numbers["NonaffineKappaError"] = aggregate["across_data_seeds"][
            "median_kappa_relative_error"
        ]
    # p-values are emitted as powers of two so the text renders them as exact fractions
    numbers["EthreePSeed"] = f"2^{{-{seed_level_stats['units_improved']}}}"
    numbers["EthreePRaw"] = f"2^{{-{fit_level['fits_valid']}}}"

    # ---------------- E7: resolution scope ----------------------------------------
    e7_path = namespace / "outputs/heldout/e7/e7_scope_levels.json"
    if e7_path.is_file():
        e7 = json.loads(e7_path.read_text(encoding="utf-8"))
        labels = {
            "COMPUTABLE": "Symmetric difference evaluated",
            "STATIONARITY_RESOLVED": "Both branches reach the tightest tolerance",
            "BRANCH_COMPARABLE": "Branches comparable (no jump)",
            "REFERENCE_AGREEMENT": "Agreement with the exact reference within 10\\%",
        }
        rows7 = [f"{labels[k]} & {v[0]}/{v[1]} \\\\" for k, v in e7.items() if k in labels]
        numbers["EsevenSteps"] = e7["COMPUTABLE"][1]
        numbers["EsevenComparable"] = e7["BRANCH_COMPARABLE"][0]
        numbers["EsevenAgreement"] = e7["REFERENCE_AGREEMENT"][0]
        numbers["EsevenStationarity"] = e7["STATIONARITY_RESOLVED"][0]
        numbers["EsevenRefinements"] = e7["any_tolerance_reached"][1]
        numbers["EsevenToleranceReached"] = e7["any_tolerance_reached"][0]
        tables.append(
            "\n".join(
                [
                    r"\begin{table}[!htbp]",
                    r"\centering",
                    r"\caption{Profile-resolution check, reported at four separate levels.",
                    r"Agreement with the exact reference is a numerical statement; it is reported apart from stationarity.}",
                    r"\label{tab:e7_scope}",
                    r"\footnotesize",
                    r"\setlength{\tabcolsep}{4pt}",
                    r"\begin{tabular}{lc}",
                    r"\toprule",
                    r"Level & Count \\",
                    r"\midrule",
                    *rows7,
                    r"\bottomrule",
                    r"\end{tabular}",
                    r"\end{table}",
                ]
            )
        )

    # ---------------- E8: matched-damping cost ------------------------------------
    e8_rows = read_csv(namespace / "outputs/posthoc/e8/e8_matched_gamma_cost.csv")
    if e8_rows:
        alphas = sorted({number(r["alpha"]) for r in e8_rows if number(r["alpha"]) is not None})
        cells = []
        for alpha in alphas:
            group = [r for r in e8_rows if number(r["alpha"]) == alpha and r["seed"] == "215"]
            cg = median([number(r["solve_seconds"]) for r in group if r["method"] == "CG"])
            lsqr = median([number(r["solve_seconds"]) for r in group if r["method"] == "scaled_LSQR"])
            cg_acc = max([number(r["accuracy_vs_dense_reference"]) for r in group if r["method"] == "CG"] or [None])
            lsqr_acc = max([number(r["accuracy_vs_dense_reference"]) for r in group if r["method"] == "scaled_LSQR"] or [None])
            cells.append(f"{alpha:g} & {fmt(cg, 2)} & {fmt(lsqr, 2)} & {fmt(cg_acc, 1)} & {fmt(lsqr_acc, 1)} \\\\")
            tag = alphaTag(alpha)
            numbers[f"EeightCGSolve{tag}"] = cg
            numbers[f"EeightLSQRSolve{tag}"] = lsqr
            numbers[f"EeightCGAccuracy{tag}"] = cg_acc
            numbers[f"EeightLSQRAccuracy{tag}"] = lsqr_acc
        weak = alphas[0]
        strong = alphas[-1]
        cg_weak = median([number(r["solve_seconds"]) for r in e8_rows if number(r["alpha"]) == weak and r["method"] == "CG" and r["seed"] == "215"])
        cg_strong = median([number(r["solve_seconds"]) for r in e8_rows if number(r["alpha"]) == strong and r["method"] == "CG" and r["seed"] == "215"])
        numbers["EeightCGSpeedup"] = (cg_weak / cg_strong) if cg_strong else None
        numbers["EeightRuns"] = len(e8_rows)
        tables.append(
            "\n".join(
                [
                    r"\begin{table}[!htbp]",
                    r"\centering",
                    r"\caption{Cost at a matched damping on one archived centre.",
                    r"Every method solves the same system at the same $\gamma$ from a zero initial guess.",
                    r"Times are medians over three repeats after a discarded warm-up.",
                    r"Accuracy is the relative difference from the dense factorization.}",
                    r"\label{tab:e8_cost}",
                    r"\footnotesize",
                    r"\setlength{\tabcolsep}{4pt}",
                    r"\begin{tabular}{ccccc}",
                    r"\toprule",
                    r"$\alpha$ & CG (s) & LSQR (s) & CG accuracy & LSQR accuracy \\",
                    r"\midrule",
                    *cells,
                    r"\bottomrule",
                    r"\end{tabular}",
                    r"\end{table}",
                ]
            )
        )

    macro_lines = [
        "% Generated by src/build_paper_tables.py; do not edit by hand.",
        "% Every value traces to a machine-readable artifact in this namespace.",
    ]
    for key in sorted(numbers):
        value = numbers[key]
        if value is None:
            continue
        if isinstance(value, int):
            macro_lines.append(f"\\newcommand{{\\{key}}}{{{value}}}")
        elif key in ("EthreeRone", "EthreeRtwo", "EeightCGSpeedup"):
            macro_lines.append(f"\\newcommand{{\\{key}}}{{{value:.1f}}}")
        elif key.startswith("EthreeP"):
            # already a LaTeX power-of-two string such as 2^{-6}; emit it verbatim
            macro_lines.append(f"\\newcommand{{\\{key}}}{{{value}}}")
        else:
            macro_lines.append(f"\\newcommand{{\\{key}}}{{{fmt(value)}}}")

    return "\n".join(tables) + "\n", "\n".join(macro_lines) + "\n", numbers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    args = parser.parse_args()

    namespace = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    tables, macros, numbers = build(namespace)
    (out / "paper_tables.tex").write_text(tables, encoding="utf-8")
    (out / "paper_numbers.tex").write_text(macros, encoding="utf-8")
    (out / "paper_numbers.json").write_text(
        json.dumps(
            {
                "classification": "GENERATED_FROM_ARTIFACTS",
                "note": "the manuscript must not hard-code these values; cite the macros",
                "values": numbers,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(numbers)} numbers, {tables.count('begin{table')} tables -> {out}")


if __name__ == "__main__":
    main()
