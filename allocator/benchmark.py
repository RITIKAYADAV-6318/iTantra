"""
Day 3: QIEA vs Greedy Benchmark

Compares the Greedy and QIEA allocators across multiple channel
bitrates and generates a Quality-vs-Bitrate curve.
"""

import matplotlib

import matplotlib.pyplot as plt

from allocator.allocator import BandwidthAllocator
from allocator.quantum_allocator import allocate_qiea, calculate_priority

# Shared config for BOTH allocators. Passing the exact same values to
# greedy and QIEA guarantees they compute the same max_slots budget at
# each bitrate, so the curve compares search quality, not accidental
# config drift between the two constructors' defaults.
REFERENCE_BITRATE_KBPS = 8.0
MIN_PROTECT_FRACTION = 0.15

# Both allocators are scored and optimized against this SAME priority
# formula (matches allocate_greedy's own scoring), so "who protected
# more of what actually mattered" is a fair, apples-to-apples number.
PRIORITY_MODE = "weighted_sum"


def calculate_retained_quality(packet, priority, protection_threshold=0.5):
    """
    Sum of priority for tokens that were protected at all (binary),
    NOT weighted by the continuous protection strength value.

    Why binary: QuantumAllocator._build_protection_values tapers
    protection strength by rank within the selected set (top token
    gets 1.0, lower-ranked selected tokens get as low as 0.6), while a
    simple greedy implementation typically gives every selected token
    full strength (1.0). If this metric multiplied by the raw
    protection value, it would silently score allocators on their
    protection-value convention rather than on which tokens they
    selected -- exactly the kind of formula mismatch this benchmark
    exists to avoid. Binary selection isolates the comparison to what
    we actually want to measure: did the search protect the tokens
    that mattered, within the same bitrate budget.
    """

    if packet is None:
        return 0.0

    protection = getattr(packet, "protection_per_token", None)

    if not protection:
        return 0.0

    count = min(len(priority), len(protection))

    return sum(
        priority[i]
        for i in range(count)
        if protection[i] > protection_threshold
    )


def run_benchmark():
    print("Initializing QIEA vs Greedy Benchmark...")

    text = (
        "Commander Sharma emergency medical evacuation "
        "required immediately at 28.5N 77.1E"
    )

    tokens = text.split()
    n = len(tokens)

    confidence = [
        0.9, 0.9, 0.8, 0.8, 0.8,
        0.9, 0.7, 0.9, 0.4, 0.4
    ]

    criticality = [
        0.8, 0.8, 1.0, 1.0, 1.0,
        0.5, 1.0, 0.2, 1.0, 1.0
    ]

    if len(confidence) != n or len(criticality) != n:
        raise ValueError(
            f"Token metadata mismatch: "
            f"{n} tokens, {len(confidence)} confidence values, "
            f"{len(criticality)} criticality values."
        )

    priority = calculate_priority(
        confidence,
        criticality,
        priority_mode=PRIORITY_MODE,
    )

    greedy_engine = BandwidthAllocator(
        reference_bitrate_kbps=REFERENCE_BITRATE_KBPS,
        min_protect_fraction=MIN_PROTECT_FRACTION,
    )

    bitrates = [
        0.5, 1.0, 2.0, 3.0, 4.0,
        5.0, 6.0, 7.0, 8.0
    ]

    greedy_scores = []
    qiea_scores = []

    print()
    print(
        f"{'Bitrate (kbps)':<16}"
        f"| {'Greedy Quality':<17}"
        f"| {'QIEA Quality':<15}"
        f"| Winner"
    )
    print("-" * 70)

    for bitrate in bitrates:

        greedy_packet = greedy_engine.allocate(
            text=text,
            confidence=confidence,
            criticality=criticality,
            channel_bitrate_kbps=bitrate,
            language="en"
        )

        greedy_score = calculate_retained_quality(
            greedy_packet,
            priority
        )

        qiea_packet = allocate_qiea(
            text=text,
            confidence=confidence,
            criticality=criticality,
            channel_bitrate_kbps=bitrate,
            language="en",
            reference_bitrate_kbps=REFERENCE_BITRATE_KBPS,
            min_protect_fraction=MIN_PROTECT_FRACTION,
            priority_mode=PRIORITY_MODE,
        )

        qiea_score = calculate_retained_quality(
            qiea_packet,
            priority
        )

        greedy_scores.append(greedy_score)
        qiea_scores.append(qiea_score)

        difference = qiea_score - greedy_score

        if difference > 0.01:
            winner = "QIEA"
        elif difference < -0.01:
            winner = "Greedy"
        else:
            winner = "Tie"

        print(
            f"{bitrate:<16.1f}"
            f"| {greedy_score:<17.4f}"
            f"| {qiea_score:<15.4f}"
            f"| {winner}"
        )

    plt.figure(figsize=(10, 6))

    plt.plot(
        bitrates,
        greedy_scores,
        marker="o",
        linestyle="-",
        label="Greedy Allocator (Baseline)"
    )

    plt.plot(
        bitrates,
        qiea_scores,
        marker="s",
        linestyle="-",
        label="QIEA Allocator (Quantum-Inspired)"
    )

    plt.title(
        "Quality-vs-Bitrate Benchmark: QIEA vs Greedy",
        fontsize=14,
        fontweight="bold"
    )

    plt.xlabel(
        "Channel Bitrate (kbps)",
        fontsize=12
    )

    plt.ylabel(
        "Critical Quality Retained",
        fontsize=12
    )

    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend(fontsize=11)
    plt.tight_layout()

    output_file = "QIEA_Benchmark_Curve.png"

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    print()
    print("Benchmark complete!")
    print(f"Graph saved as: {output_file}")

    # plt.show() throws/hangs on machines with no display (headless
    # CI, some judge laptops without a GUI backend). The PNG is
    # already saved above regardless, so failing to pop up a window
    # should never crash the benchmark run.
    try:
        plt.show()
    except Exception as error:
        print(
            f"(Skipped interactive plot window: {error}. "
            f"The saved PNG above is unaffected.)"
        )


if __name__ == "__main__":
    run_benchmark()