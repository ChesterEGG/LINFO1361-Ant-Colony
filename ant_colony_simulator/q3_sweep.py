"""
Sweep script pour évaluer l'impact des Cheaters.
Génère les Figures 4 (Steps), 5 (Temps) et 6 (Throughput).
Objectif : 75% collectée, 33% rapportée à la colonie.
"""

import argparse
import csv
import math
import os
import statistics as stats
import time
import random

from utils import create_environment, add_ants


def parse_pct_list(s: str):
    """Parse une liste de pourcentages séparés par des virgules"""
    return [float(x.strip()) for x in s.split(',') if x.strip()]


def run_once(env_path, smart_file, cheater_file, total_ants, cheater_pct, max_steps, time_limit, seed=None):
    if seed is not None:
        random.seed(seed)

    env = create_environment(env_path, 100, 100, verbose=False)

    # Calcul du nombre de fourmis pour chaque stratégie
    num_cheaters = int(total_ants * (cheater_pct / 100.0))
    num_smart = total_ants - num_cheaters

    # Ajout des fourmis normales
    if num_smart > 0:
        add_ants(env, "smart", smart_file, num_smart, verbose=False)

    # Ajout des fourmis tricheuses
    if num_cheaters > 0:
        add_ants(env, "cheater", cheater_file, num_cheaters, verbose=False)

    # INJECTION : Donner l'environnement global uniquement aux cheaters
    for ant in env.ants:
        if hasattr(ant.strategy, "set_environment"):
            ant.strategy.set_environment(env)

    start = time.time()
    steps = 0
    initial_food = env.initial_food_amount

    if initial_food <= 0:
        raise ValueError("L'environnement ne contient aucune nourriture.")

    success = False
    while steps < max_steps and (time.time() - start) < time_limit:
        env.update()
        steps += 1

        collected_ratio = env.food_removed / initial_food  # Ramassé
        returned_ratio = env.food_collected / initial_food  # Déposé

        # Objectif : 75% enlevé et 33% retourné
        if collected_ratio >= 0.75 and returned_ratio >= 0.33:
            success = True
            break

    elapsed = time.time() - start

    # Calcul du Throughput (Steps par seconde)
    throughput = steps / elapsed if elapsed > 0 else 0

    return {
        "cheater_pct": cheater_pct,
        "smart_ants": num_smart,
        "cheater_ants": num_cheaters,
        "steps": steps,
        "time_s": elapsed,
        "throughput": throughput,
        "success": success,
        "food_removed": env.food_removed,
        "food_collected": env.food_collected,
        "total_food": initial_food,
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
    parser.add_argument("--smart-strategy", default="strategies/smart.py")
    parser.add_argument("--cheater-strategy", default="strategies/cheater.py")
    parser.add_argument("--total-ants", type=int, default=100, help="Nombre total de fourmis dans la simulation")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--pct-list", default="0,10,20,30,40,50,60,70,80,90,100",
                        help="Liste des % de cheaters à tester")
    parser.add_argument("--max-steps", type=int, default=10000)
    parser.add_argument("--time-limit", type=float, default=300)
    parser.add_argument("--out-prefix", default="cheater_results")
    parser.add_argument("--seed", type=int, default=1361)
    args = parser.parse_args()

    if not os.path.exists(args.env):
        raise FileNotFoundError(f"Fichier d'environnement introuvable : {args.env}")
    if not os.path.exists(args.smart_strategy):
        raise FileNotFoundError(f"Stratégie smart introuvable : {args.smart_strategy}")
    if not os.path.exists(args.cheater_strategy):
        raise FileNotFoundError(f"Stratégie cheater introuvable : {args.cheater_strategy}")

    pct_values = parse_pct_list(args.pct_list)
    raw_rows = []
    summary_rows = []

    total = len(pct_values) * args.runs
    done = 0

    for pct in pct_values:
        step_values = []
        time_values = []
        throughput_values = []
        success_count = 0

        for r in range(args.runs):
            done += 1
            seed = args.seed + int(pct) * 1000 + r
            print(f"[{done}/{total}] cheaters={pct}%, run={r + 1}/{args.runs}", flush=True)

            row = run_once(
                args.env, args.smart_strategy, args.cheater_strategy,
                args.total_ants, pct, args.max_steps, args.time_limit, seed=seed
            )
            row["run"] = r + 1
            raw_rows.append(row)

            if row["success"]:
                step_values.append(row["steps"])
                time_values.append(row["time_s"])
                throughput_values.append(row["throughput"])
                success_count += 1
            else:
                step_values.append(args.max_steps)
                time_values.append(args.time_limit)
                # Le throughput en cas d'échec est calculé sur le temps max
                throughput_values.append(args.max_steps / args.time_limit)

        steps_mean, steps_std = mean_std(step_values)
        time_mean, time_std = mean_std(time_values)
        tp_mean, tp_std = mean_std(throughput_values)

        summary_rows.append({
            "cheater_pct": pct,
            "runs": args.runs,
            "successes": success_count,
            "steps_mean": steps_mean,
            "steps_std": steps_std,
            "time_mean_s": time_mean,
            "time_std_s": time_std,
            "throughput_mean": tp_mean,
            "throughput_std": tp_std,
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

    print(f"\nSauvegardé : {raw_csv}")
    print(f"Sauvegardé : {summary_csv}")

    # --- GÉNÉRATION DES GRAPHIQUES ---
    try:
        import matplotlib.pyplot as plt

        xs = [row["cheater_pct"] for row in summary_rows]

        steps_mean = [row["steps_mean"] for row in summary_rows]
        steps_std = [row["steps_std"] for row in summary_rows]

        time_mean = [row["time_mean_s"] for row in summary_rows]
        time_std = [row["time_std_s"] for row in summary_rows]

        tp_mean = [row["throughput_mean"] for row in summary_rows]
        tp_std = [row["throughput_std"] for row in summary_rows]

        # FIGURE 4 : Steps en fonction du % de cheaters
        plt.figure()
        plt.errorbar(xs, steps_mean, yerr=steps_std, marker="o", capsize=4, color="blue")
        plt.xlabel("Pourcentage de cheaters (%)")
        plt.ylabel("Steps moyens nécessaires")
        plt.title("Figure 4: Nombre de steps selon le % de cheaters")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.out_prefix + "_figure4_steps.png", dpi=200)

        # FIGURE 5 : Temps réel en fonction du % de cheaters
        plt.figure()
        plt.errorbar(xs, time_mean, yerr=time_std, marker="o", capsize=4, color="red")
        plt.xlabel("Pourcentage de cheaters (%)")
        plt.ylabel("Temps moyen (secondes)")
        plt.title("Figure 5: Temps d'exécution réel selon le % de cheaters")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.out_prefix + "_figure5_time.png", dpi=200)

        # FIGURE 6 : Throughput en fonction du % de cheaters
        plt.figure()
        plt.errorbar(xs, tp_mean, yerr=tp_std, marker="o", capsize=4, color="green")
        plt.xlabel("Pourcentage de cheaters (%)")
        plt.ylabel("Throughput (steps/seconde)")
        plt.title("Figure 6: Throughput selon le % de cheaters")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.out_prefix + "_figure6_throughput.png", dpi=200)

        print(f"Graphiques générés :")
        print(f" -> {args.out_prefix}_figure4_steps.png")
        print(f" -> {args.out_prefix}_figure5_time.png")
        print(f" -> {args.out_prefix}_figure6_throughput.png")

    except Exception as e:
        print(f"Erreur lors de la génération des graphiques : {e}")


if __name__ == "__main__":
    main()