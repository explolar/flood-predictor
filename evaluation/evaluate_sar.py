"""SAR flood detection evaluation harness.

Runs detection across benchmark AOIs, computes accuracy metrics,
and produces a JSON report with per-AOI and aggregate results.

Usage:
    python -m evaluation.evaluate_sar [--strategies event_pair seasonal_baseline] [--thresholds 2.0 3.0 4.0]
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.benchmark_aois import BENCHMARK_AOIS


def _compute_metrics(predicted_ha: float, expected_ha: float, is_flood: bool):
    """Compute per-AOI evaluation metrics.

    Returns dict with:
      - hit: True if detection agrees with label (flood found where expected, or not found where not expected)
      - area_error_ha: predicted - expected
      - area_error_pct: relative error (None if expected is 0)
      - false_positive: non-flood AOI where flood was detected
      - false_negative: flood AOI where no flood was detected
    """
    detected = predicted_ha > 50  # minimum 50 ha to count as detection
    hit = (detected and is_flood) or (not detected and not is_flood)
    false_positive = detected and not is_flood
    false_negative = not detected and is_flood
    area_error = predicted_ha - expected_ha
    area_error_pct = (area_error / expected_ha * 100) if expected_ha > 0 else None

    return {
        "hit": hit,
        "area_error_ha": round(area_error, 1),
        "area_error_pct": round(area_error_pct, 1) if area_error_pct is not None else None,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "detected": detected,
    }


def run_evaluation(strategies=None, thresholds=None, polarization="VH", speckle=True):
    """Run SAR detection across all benchmark AOIs for given strategy/threshold combos.

    Returns list of result dicts.
    """
    if strategies is None:
        strategies = ["event_pair"]
    if thresholds is None:
        thresholds = [3.0]

    from api.dependencies import initialize_ee_api
    from gee_functions.sar import get_all_sar_data

    initialize_ee_api()

    results = []

    for aoi in BENCHMARK_AOIS:
        aoi_json = json.dumps(aoi["geojson"])

        for strategy in strategies:
            for threshold in thresholds:
                print(f"  [{aoi['name']}] strategy={strategy} threshold={threshold}...", flush=True)
                t0 = time.time()
                try:
                    result = get_all_sar_data(
                        aoi_json,
                        aoi["f_start"],
                        aoi["f_end"],
                        aoi["p_start"],
                        aoi["p_end"],
                        threshold,
                        polarization,
                        speckle,
                        reference_strategy=strategy,
                    )
                    predicted_ha = result.get("area_ha", 0)
                    quality = result.get("quality", {})
                except Exception as e:
                    predicted_ha = 0
                    quality = {"error": str(e)}

                elapsed = round(time.time() - t0, 1)
                metrics = _compute_metrics(predicted_ha, aoi["expected_area_ha"] or 0, aoi["is_flood"])

                results.append(
                    {
                        "aoi_name": aoi["name"],
                        "is_flood": aoi["is_flood"],
                        "expected_area_ha": aoi["expected_area_ha"],
                        "predicted_area_ha": predicted_ha,
                        "strategy": strategy,
                        "threshold": threshold,
                        "elapsed_s": elapsed,
                        "quality": quality,
                        **metrics,
                    }
                )

    return results


def aggregate_metrics(results):
    """Compute aggregate metrics across all results."""
    total = len(results)
    if total == 0:
        return {}

    hits = sum(1 for r in results if r["hit"])
    fps = sum(1 for r in results if r["false_positive"])
    fns = sum(1 for r in results if r["false_negative"])
    flood_aois = [r for r in results if r["is_flood"]]
    control_aois = [r for r in results if not r["is_flood"]]

    # F1-like: TP / (TP + 0.5*(FP+FN))
    tp = sum(1 for r in results if r["detected"] and r["is_flood"])
    precision = tp / max(tp + fps, 1)
    recall = tp / max(tp + fns, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    # Area error stats for flood AOIs only
    area_errors = [r["area_error_pct"] for r in flood_aois if r["area_error_pct"] is not None]

    return {
        "total_aois": total,
        "overall_accuracy": round(hits / total, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "false_positives": fps,
        "false_negatives": fns,
        "dry_scene_false_positive_rate": round(fps / max(len(control_aois), 1), 3),
        "mean_area_error_pct": round(sum(area_errors) / max(len(area_errors), 1), 1) if area_errors else None,
    }


def main():
    parser = argparse.ArgumentParser(description="SAR flood detection evaluation")
    parser.add_argument("--strategies", nargs="+", default=["event_pair", "seasonal_baseline"])
    parser.add_argument("--thresholds", nargs="+", type=float, default=[2.0, 3.0, 4.0])
    parser.add_argument("--output", default="evaluation/results.json")
    args = parser.parse_args()

    print(
        f"Running evaluation: {len(BENCHMARK_AOIS)} AOIs x {len(args.strategies)} strategies x {len(args.thresholds)} thresholds"
    )
    results = run_evaluation(strategies=args.strategies, thresholds=args.thresholds)
    agg = aggregate_metrics(results)

    report = {
        "aggregate": agg,
        "per_aoi": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nResults written to {output_path}")
    print(
        f"Aggregate: accuracy={agg.get('overall_accuracy')}, F1={agg.get('f1')}, FP rate={agg.get('dry_scene_false_positive_rate')}"
    )


if __name__ == "__main__":
    main()
