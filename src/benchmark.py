"""Benchmarktests fuer den Tablut-Zuggenerator.

Starten:
    python -m src.benchmark

Misst:
- Zeit fuer 10000 Aufrufe von generate_legal_moves()
- Anzahl legaler Zuege pro Stellung
- Rechner-/Python-Konfiguration
"""

import csv
import os
import platform
import sys
import time

from src.fen import STARTING_FEN, parse_fen
from src.moves import generate_legal_moves

REPETITIONS = 10_000


POSITIONS = {
    "Startstellung": STARTING_FEN,
    # Synthetic midgame position for repeatable move-generation measurements.
    "Mittelspiel": "3rrr3/4r4/4R4/r2R4r/rrR1K1Rrr/r4R2r/4R4/4r4/3rrr3 s 0 1",
    # King on b2, attacker on d3, White to move.
    "Endspiel": "9/9/9/9/9/9/3r5/1K7/9 w 0 1",
}


def get_system_info():
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_cores": os.cpu_count(),
    }


def benchmark_move_generator(name, fen, repetitions=REPETITIONS):
    board = parse_fen(fen)

    # Warm-up, damit einmalige Initialisierung nicht mitgemessen wird
    for _ in range(100):
        list(generate_legal_moves(board, board.side_to_move))

    start = time.perf_counter()

    last_move_count = 0

    for _ in range(repetitions):
        moves = list(generate_legal_moves(board, board.side_to_move))
        last_move_count = len(moves)

    end = time.perf_counter()

    total_seconds = end - start
    avg_microseconds = (total_seconds / repetitions) * 1_000_000

    return {
        "position": name,
        "fen": fen,
        "legal_moves": last_move_count,
        "repetitions": repetitions,
        "total_seconds": total_seconds,
        "avg_microseconds_per_call": avg_microseconds,
    }


def run_all_benchmarks():
    print("=== Tablut Zuggenerator Benchmark ===")
    print()

    info = get_system_info()

    print("Rechnerkonfiguration:")
    print(f"Python: {info['python']}")
    print(f"Platform: {info['platform']}")
    print(f"Processor: {info['processor']}")
    print(f"CPU cores: {info['cpu_cores']}")
    print()
    print(f"Wiederholungen pro Stellung: {REPETITIONS}")
    print()

    results = []

    for name, fen in POSITIONS.items():
        result = benchmark_move_generator(name, fen)
        results.append(result)

        print(f"--- {result['position']} ---")
        print(f"FEN: {result['fen']}")
        print(f"Legale Zuege: {result['legal_moves']}")
        print(
            f"Zeit fuer {result['repetitions']} Ausfuehrungen: {result['total_seconds']:.6f} s"
        )
        print(f"Durchschnitt pro Aufruf: {result['avg_microseconds_per_call']:.3f} µs")
        print()

    write_csv(results, info)


def write_csv(results, info):
    platform_name = info["platform"].lower()
    if "windows" in platform_name:
        suffix = "windows"
    elif "macos" in platform_name or "darwin" in platform_name:
        suffix = "mac"
    elif "linux" in platform_name:
        suffix = "linux"
    else:
        suffix = "unknown"
    filename = f"benchmark_results_{suffix}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")

        writer.writerow(["Rechnerkonfiguration"])
        writer.writerow(["Python", info["python"]])
        writer.writerow(["Platform", info["platform"]])
        writer.writerow(["Processor", info["processor"]])
        writer.writerow(["CPU cores", info["cpu_cores"]])
        writer.writerow([])

        writer.writerow(
            [
                "Position",
                "FEN",
                "Legale Zuege",
                "Wiederholungen",
                "Sekunden",
                "Mikrosekunden pro Aufruf",
            ]
        )

        for result in results:
            writer.writerow(
                [
                    result["position"],
                    result["fen"],
                    result["legal_moves"],
                    result["repetitions"],
                    f"{result['total_seconds']:.6f}",
                    f"{result['avg_microseconds_per_call']:.3f}",
                ]
            )

    print(f"CSV gespeichert als: {filename}")


if __name__ == "__main__":
    run_all_benchmarks()
