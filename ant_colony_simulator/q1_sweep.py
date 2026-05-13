"""
Q1 sweep for LINFO1361 Assignment 3.
Runs SmartStrategy on 05_square_four_food_spots with different ant counts.
Objective used for Q1 report: 75% food removed and 33% food returned to colony.
"""

import argparse
import csv
import math
import os
import statistics as stats
import time
import random

from utils import create_environment, add_ants


def parse_ants_list(s: str):
    return [int(x.strip()) for x in s.split(',') if x.strip()]


def run_once(env_path, strategy_file, ants, max_steps, time_limit, seed=None):
    if seed is not None:
        random.seed(seed)

    env = create_environment(env_path, 100, 100, verbose=False)

    # Force Q1 ant count. We intentionally ignore ANTS inside the env file,
    # because Q1 asks us to vary the number of ants.
    add_ants(env, "smart", strategy_file, ants, verbose=False)

    start = time.time()
    steps = 0
    initial_food = env.initial_food_amount

    if initial_food <= 0:
        raise ValueError("The environment contains no food.")

    success = False
    while steps < max_steps and (time.time() - start) < time_limit:
        env.update()
        steps += 1

        collected_ratio = env.food_removed / initial_food      # food picked up from sources
        returned_ratio = env.food_collected / initial_food     # food dropped at colony

        if collected_ratio >= 0.75 and returned_ratio >= 0.33:
            success = True
            break

    elapsed = time.time() - start
    return {
        "ants": ants,
        "steps": steps,
        "time_s": elapsed,
        "success": success,
        "food_removed": env.food_removed,
        "food_collected": env.food_collected,
        "total_food": initial_food,
        "removed_pct": 100 * env.food_removed / initial_food,
        "returned_pct": 100 * env.food_collected / initial_food,
    }


def mean_std(values):
    if not values:
        return math.nan, math.nan
    if len(values) == 1:
        return values[0], 0.0
    return stats.mean(values), stats.stdev(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="envs/05_square_four_food_spots.txt")
    parser.add_argument("--strategy-file", default="strategies/smart.py")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--ants-list", default="1,20,40,60,80,100,120,140,160,180,200")
    parser.add_argument("--max-steps", type=int, default=10000)
    parser.add_argument("--time-limit", type=float, default=300)
    parser.add_argument("--out-prefix", default="q1_results")
    parser.add_argument("--seed", type=int, default=1361)
    args = parser.parse_args()

    if not os.path.exists(args.env):
        raise FileNotFoundError(
            f"Environment file not found: {args.env}\n"
            "Place 05_square_four_food_spots.txt in an envs/ folder, "
            "or pass its path with --env."
        )
    if not os.path.exists(args.strategy_file):
        raise FileNotFoundError(f"Strategy file not found: {args.strategy_file}")

    ants_values = parse_ants_list(args.ants_list)
    raw_rows = []
    summary_rows = []

    total = len(ants_values) * args.runs
    done = 0

    for ants in ants_values:
        step_values = []
        time_values = []
        success_count = 0

        for r in range(args.runs):
            done += 1
            seed = args.seed + ants * 1000 + r
            print(f"[{done}/{total}] ants={ants}, run={r+1}/{args.runs}", flush=True)
            row = run_once(args.env, args.strategy_file, ants, args.max_steps, args.time_limit, seed=seed)
            row["run"] = r + 1
            raw_rows.append(row)

            if row["success"]:
                step_values.append(row["steps"])
                time_values.append(row["time_s"])
                success_count += 1
            else:
                # Keep failed runs visible in raw CSV; summary uses max limit for steps/time.
                step_values.append(args.max_steps)
                time_values.append(args.time_limit)

        steps_mean, steps_std = mean_std(step_values)
        time_mean, time_std = mean_std(time_values)
        summary_rows.append({
            "ants": ants,
            "runs": args.runs,
            "successes": success_count,
            "steps_mean": steps_mean,
            "steps_std": steps_std,
            "time_mean_s": time_mean,
            "time_std_s": time_std,
        })

    raw_csv = args.out_prefix + "_raw.csv"
    summary_csv = args.out_prefix + "_summary.csv"

    with open(raw_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        writer.writeheader()
        writer.writerows(raw_rows)

    with open(summary_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nSaved {raw_csv}")
    print(f"Saved {summary_csv}")

    try:
        import matplotlib.pyplot as plt

        xs = [row["ants"] for row in summary_rows]
        steps_mean = [row["steps_mean"] for row in summary_rows]
        steps_std = [row["steps_std"] for row in summary_rows]
        time_mean = [row["time_mean_s"] for row in summary_rows]
        time_std = [row["time_std_s"] for row in summary_rows]

        plt.figure()
        plt.errorbar(xs, steps_mean, yerr=steps_std, marker="o", capsize=4)
        plt.xlabel("Nombre de fourmis")
        plt.ylabel("Steps moyens")
        plt.title("Q1 — Steps nécessaires selon le nombre de fourmis")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.out_prefix + "_steps.png", dpi=200)

        plt.figure()
        plt.errorbar(xs, time_mean, yerr=time_std, marker="o", capsize=4)
        plt.xlabel("Nombre de fourmis")
        plt.ylabel("Temps moyen (s)")
        plt.title("Q1 — Temps d'exécution selon le nombre de fourmis")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.out_prefix + "_time.png", dpi=200)

        print(f"Saved {args.out_prefix}_steps.png")
        print(f"Saved {args.out_prefix}_time.png")
    except Exception as e:
        print(f"Could not generate plots automatically: {e}")

    best = min(summary_rows, key=lambda row: row["steps_mean"])
    print("\nBest by mean steps:")
    print(best)


if __name__ == "__main__":
    main()
