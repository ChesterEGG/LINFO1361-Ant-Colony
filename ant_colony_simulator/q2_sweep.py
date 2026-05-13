"""
Q2 sweep for LINFO1361 Assignment 3.
Runs SmartStrategy on 05_square_four_food_spots with different pheromone evaporation rates.
Objective used for Q2 report: 75% food removed and 33% food returned to colony.
"""

import argparse
import csv
import math
import os
import random
import statistics as stats
import time

from utils import create_environment, add_ants


def make_rates(n=20, start=0.500, end=0.999):
    if n == 1:
        return [start]
    step = (end - start) / (n - 1)
    return [round(start + i * step, 6) for i in range(n)]


def parse_rates(s: str):
    return [float(x.strip()) for x in s.split(',') if x.strip()]


def run_once(env_path, strategy_file, evaporation_rate, ants, max_steps, time_limit, seed=None):
    if seed is not None:
        random.seed(seed)

    env = create_environment(env_path, 100, 100, verbose=False)

    # Force the evaporation rate for both pheromone maps.
    env.home_pheromones.evaporation_rate = evaporation_rate
    env.food_pheromones.evaporation_rate = evaporation_rate

    # Force Q2 ant count. Q2 asks for 70 ants.
    add_ants(env, "smart", strategy_file, ants, verbose=False)

    start_time = time.time()
    steps = 0
    initial_food = env.initial_food_amount
    if initial_food <= 0:
        raise ValueError("The environment contains no food.")

    success = False
    while steps < max_steps and (time.time() - start_time) < time_limit:
        env.update()
        steps += 1

        collected_ratio = env.food_removed / initial_food
        returned_ratio = env.food_collected / initial_food
        if collected_ratio >= 0.75 and returned_ratio >= 0.33:
            success = True
            break

    elapsed = time.time() - start_time
    return {
        "evaporation_rate": evaporation_rate,
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
    parser.add_argument("--ants", type=int, default=70)
    parser.add_argument("--num-rates", type=int, default=20)
    parser.add_argument("--rates", default=None, help="Optional comma-separated rates. If omitted, uses 20 values from 0.500 to 0.999.")
    parser.add_argument("--max-steps", type=int, default=10000)
    parser.add_argument("--time-limit", type=float, default=300)
    parser.add_argument("--out-prefix", default="q2_results")
    parser.add_argument("--seed", type=int, default=2361)
    args = parser.parse_args()

    if not os.path.exists(args.env):
        raise FileNotFoundError(f"Environment file not found: {args.env}")
    if not os.path.exists(args.strategy_file):
        raise FileNotFoundError(f"Strategy file not found: {args.strategy_file}")

    rates = parse_rates(args.rates) if args.rates else make_rates(args.num_rates)
    raw_rows = []
    summary_rows = []

    total = len(rates) * args.runs
    done = 0

    for rate in rates:
        step_values = []
        time_values = []
        success_count = 0

        for r in range(args.runs):
            done += 1
            seed = args.seed + int(rate * 1_000_000) + r
            print(f"[{done}/{total}] evaporation={rate:.6f}, run={r+1}/{args.runs}", flush=True)
            row = run_once(args.env, args.strategy_file, rate, args.ants, args.max_steps, args.time_limit, seed=seed)
            row["run"] = r + 1
            raw_rows.append(row)

            if row["success"]:
                step_values.append(row["steps"])
                time_values.append(row["time_s"])
                success_count += 1
            else:
                step_values.append(args.max_steps)
                time_values.append(args.time_limit)

        steps_mean, steps_std = mean_std(step_values)
        time_mean, time_std = mean_std(time_values)
        summary_rows.append({
            "evaporation_rate": rate,
            "ants": args.ants,
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

        xs = [row["evaporation_rate"] for row in summary_rows]
        steps_mean = [row["steps_mean"] for row in summary_rows]
        steps_std = [row["steps_std"] for row in summary_rows]

        plt.figure()
        plt.errorbar(xs, steps_mean, yerr=steps_std, marker="o", capsize=4)
        plt.xlabel("Taux d'évaporation")
        plt.ylabel("Steps moyens")
        plt.title("Q2 — Steps selon le taux d'évaporation")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.out_prefix + "_steps.png", dpi=200)
        print(f"Saved {args.out_prefix}_steps.png")
    except Exception as e:
        print(f"Could not generate plot automatically: {e}")

    best = min(summary_rows, key=lambda row: row["steps_mean"])
    print("\nBest by mean steps:")
    print(best)


if __name__ == "__main__":
    main()
