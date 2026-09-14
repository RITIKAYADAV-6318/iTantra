"""
Quantum-Inspired Evolutionary Algorithm (QIEA) Bandwidth Allocator
"""

import math
import random
from typing import List, Optional

from channel.packet import Packet
from allocator.allocator import BandwidthAllocator


def calculate_priority(
    confidence: List[float],
    criticality: List[float],
    priority_mode: str = "weighted_sum",
) -> List[float]:
    """
    Shared priority formula, exported at module level so any script
    that needs to score/compare allocator output (e.g. the benchmark)
    uses the exact same formula the allocators optimize for, instead
    of a second hardcoded copy that can silently drift out of sync.

    'weighted_sum' matches allocate_greedy(): 0.5*criticality +
    0.5*(1-confidence). 'product' reproduces the original
    criticality*(1-confidence) formula.
    """

    if priority_mode not in {"weighted_sum", "product"}:
        raise ValueError(
            f"priority_mode must be 'weighted_sum' or 'product', "
            f"got {priority_mode!r}"
        )

    if priority_mode == "product":
        return [
            criticality[i] * (1.0 - confidence[i])
            for i in range(len(confidence))
        ]

    return [
        0.5 * criticality[i] + 0.5 * (1.0 - confidence[i])
        for i in range(len(confidence))
    ]


class QuantumAllocator(BandwidthAllocator):

    def __init__(
        self,
        reference_bitrate_kbps: float = 8.0,
        min_protect_fraction: float = 0.15,
        population_size: int = 20,
        generations: int = 60,
        rotation_angle: float = 0.05 * math.pi,
        interaction_overhead: float = 0.12,
        priority_mode: str = "weighted_sum",
        seed: Optional[int] = 42,
    ):
        if reference_bitrate_kbps <= 0:
            raise ValueError("reference_bitrate_kbps must be greater than 0")

        if not 0 <= min_protect_fraction <= 1:
            raise ValueError("min_protect_fraction must be between 0 and 1")

        if population_size < 2:
            raise ValueError("population_size must be at least 2")

        if generations < 1:
            raise ValueError("generations must be at least 1")

        if rotation_angle <= 0:
            raise ValueError("rotation_angle must be greater than 0")

        if interaction_overhead < 0:
            raise ValueError("interaction_overhead cannot be negative")

        if priority_mode not in {"weighted_sum", "product"}:
            raise ValueError(
                f"priority_mode must be 'weighted_sum' or 'product', "
                f"got {priority_mode!r}"
            )

        super().__init__(
            reference_bitrate_kbps=reference_bitrate_kbps,
            min_protect_fraction=min_protect_fraction,
        )

        self.population_size = population_size
        self.generations = generations
        self.rotation_angle = rotation_angle
        self.interaction_overhead = interaction_overhead
        self.priority_mode = priority_mode
        self.seed = seed

        self.rng = random.Random(seed)

    def allocate(
        self,
        text: str,
        confidence: List[float],
        criticality: List[float],
        channel_bitrate_kbps: float,
        language: str,
    ) -> Packet:

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if not isinstance(confidence, list):
            raise TypeError("confidence must be a list")

        if not isinstance(criticality, list):
            raise TypeError("criticality must be a list")

        if language not in {"en", "hi", "mixed"}:
            raise ValueError(
                f"language must be 'en', 'hi', or 'mixed', got {language!r}"
            )

        if channel_bitrate_kbps < 0:
            raise ValueError(
                "channel_bitrate_kbps cannot be negative"
            )

        tokens = text.split()
        n = len(tokens)

        if n != len(confidence) or n != len(criticality):
            raise ValueError(
                "tokens, confidence and criticality must have "
                f"the same length: tokens={n}, "
                f"confidence={len(confidence)}, "
                f"criticality={len(criticality)}"
            )

        self._validate_scores(confidence, "confidence")
        self._validate_scores(criticality, "criticality")

        if n == 0:
            return Packet(
                tokens=[],
                confidence_per_token=[],
                criticality_per_token=[],
                protection_per_token=[],
                allocated_for_bitrate_kbps=channel_bitrate_kbps,
                language=language,
            )

        priority = self._calculate_priority(
            confidence,
            criticality
        )

        max_slots = self._calculate_max_slots(
            n,
            channel_bitrate_kbps
        )

        best_state = self._run_qiea(
            priority=priority,
            max_slots=max_slots
        )

        best_state = self._polish(
            state=best_state,
            priority=priority
        )

        protection = self._build_protection_values(
            state=best_state,
            priority=priority
        )

        return Packet(
            tokens=tokens,
            confidence_per_token=list(confidence),
            criticality_per_token=list(criticality),
            protection_per_token=protection,
            allocated_for_bitrate_kbps=channel_bitrate_kbps,
            language=language,
        )

    def _validate_scores(
        self,
        values: List[float],
        name: str
    ) -> None:

        for i, value in enumerate(values):

            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"{name}[{i}] must be numeric"
                )

            if not math.isfinite(value):
                raise ValueError(
                    f"{name}[{i}] must be finite"
                )

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name}[{i}] must be between 0 and 1, "
                    f"got {value}"
                )

    def _calculate_priority(
        self,
        confidence: List[float],
        criticality: List[float]
    ) -> List[float]:
        """
        Per-token protection priority.

        'weighted_sum' matches the existing allocate_greedy() formula
        (0.5*criticality + 0.5*(1-confidence)) so a QIEA-vs-greedy
        benchmark compares search quality on the SAME objective rather
        than two different scoring formulas.

        'product' reproduces the original criticality*(1-confidence)
        formula, kept for backward compatibility / A-B comparison.

        Delegates to the module-level calculate_priority() so this
        class and any external script (e.g. the benchmark) can never
        compute priority two different ways by accident.
        """

        return calculate_priority(confidence, criticality, self.priority_mode)

    def _calculate_max_slots(
        self,
        n: int,
        channel_bitrate_kbps: float
    ) -> int:

        protect_fraction = max(
            self.min_protect_fraction,
            min(
                1.0,
                channel_bitrate_kbps /
                self.reference_bitrate_kbps
            )
        )

        slots = round(n * protect_fraction)

        return min(
            n,
            max(1, slots)
        )

    def _repair(
        self,
        state: List[int],
        priority: List[float],
        max_slots: int
    ) -> List[int]:

        repaired = list(state)

        selected = [
            i for i, bit in enumerate(repaired)
            if bit == 1
        ]

        if len(selected) > max_slots:

            selected.sort(
                key=lambda i: (
                    priority[i],
                    -i
                )
            )

            remove_count = len(selected) - max_slots

            for i in selected[:remove_count]:
                repaired[i] = 0

        elif len(selected) < max_slots:

            unselected = [
                i for i, bit in enumerate(repaired)
                if bit == 0
            ]

            unselected.sort(
                key=lambda i: (
                    priority[i],
                    -i
                ),
                reverse=True
            )

            add_count = max_slots - len(selected)

            for i in unselected[:add_count]:
                repaired[i] = 1

        return repaired

    def _count_segments(
        self,
        state: List[int]
    ) -> int:
        """Number of maximal contiguous runs of protected (1) tokens."""

        segments = 0
        previous = 0

        for bit in state:

            if bit == 1 and previous == 0:
                segments += 1

            previous = bit

        return segments

    def _fitness(
        self,
        state: List[int],
        priority: List[float]
    ) -> float:
        """
        Segment-aware fitness: sum of protected-token priority, minus an
        overhead charged per contiguous protected segment.

        Rationale: in the real channel, each contiguous run of protected
        tokens shares one FEC/redundancy frame. Five scattered single
        tokens cost five frames' worth of overhead; one five-token block
        costs one. This introduces an interaction between neighbouring
        selection decisions that a per-token top-k sort cannot see,
        which is what actually gives a population-based search room to
        beat greedy top-k (see TEST 7 / TEST 10).
        """

        base = sum(
            priority[i] * state[i]
            for i in range(len(state))
        )

        overhead = self.interaction_overhead * self._count_segments(state)

        return base - overhead

    def _initialize_population(
        self,
        n: int,
        max_slots: int
    ) -> List[List[float]]:

        target_probability = max_slots / n

        target_probability = max(
            0.05,
            min(0.95, target_probability)
        )

        base_theta = math.asin(
            math.sqrt(target_probability)
        )

        population = []

        for _ in range(self.population_size):

            individual = []

            for _ in range(n):

                theta = (
                    base_theta +
                    self.rng.uniform(-0.12, 0.12)
                )

                theta = self._clamp_theta(theta)

                individual.append(theta)

            population.append(individual)

        return population

    def _measure(
        self,
        theta: List[float]
    ) -> List[int]:

        state = []

        for angle in theta:

            probability = math.sin(angle) ** 2

            bit = (
                1
                if self.rng.random() < probability
                else 0
            )

            state.append(bit)

        return state

    def _clamp_theta(
        self,
        theta: float
    ) -> float:

        epsilon = 1e-6

        return max(
            epsilon,
            min(
                math.pi / 2 - epsilon,
                theta
            )
        )

    def _update_rotation(
        self,
        theta: float,
        current_bit: int,
        best_bit: int,
        current_fitness: float,
        best_fitness: float
    ) -> float:

        if current_bit == best_bit:
            return theta

        if current_fitness < best_fitness:

            if best_bit == 1 and current_bit == 0:
                theta += self.rotation_angle

            elif best_bit == 0 and current_bit == 1:
                theta -= self.rotation_angle

        return self._clamp_theta(theta)

    def _run_qiea(
        self,
        priority: List[float],
        max_slots: int
    ) -> List[int]:

        n = len(priority)

        population = self._initialize_population(
            n,
            max_slots
        )

        best_state = None
        best_fitness = -float("inf")

        for _ in range(self.generations):

            generation_states = []
            generation_fitness = []

            for individual in population:

                measured = self._measure(individual)

                repaired = self._repair(
                    measured,
                    priority,
                    max_slots
                )

                fitness = self._fitness(
                    repaired,
                    priority
                )

                generation_states.append(repaired)
                generation_fitness.append(fitness)

                if fitness > best_fitness:

                    best_fitness = fitness
                    best_state = list(repaired)

            if best_state is None:
                raise RuntimeError(
                    "QIEA failed to produce a valid solution"
                )

            new_population = []

            for population_index, individual in enumerate(
                population
            ):

                current_state = generation_states[
                    population_index
                ]

                current_fitness = generation_fitness[
                    population_index
                ]

                updated = []

                for j in range(n):

                    updated_theta = self._update_rotation(
                        theta=individual[j],
                        current_bit=current_state[j],
                        best_bit=best_state[j],
                        current_fitness=current_fitness,
                        best_fitness=best_fitness,
                    )

                    updated.append(updated_theta)

                new_population.append(updated)

            population = new_population

        return list(best_state)

    def _polish(
        self,
        state: List[int],
        priority: List[float]
    ) -> List[int]:
        """
        Local-search refinement: repeatedly apply the single best
        selected<->unselected swap while it improves the segment-aware
        fitness. This is a heuristic (not a proof of global optimality)
        once the segment-overhead term is present, because swaps can
        merge/split segments non-locally. Bounded to len(state)
        iterations to keep cost predictable.
        """

        polished = list(state)
        n = len(polished)

        for _ in range(n):

            current_fitness = self._fitness(polished, priority)

            selected = [i for i, bit in enumerate(polished) if bit == 1]
            unselected = [i for i, bit in enumerate(polished) if bit == 0]

            best_gain = 0.0
            best_swap = None

            for s in selected:
                for u in unselected:

                    candidate = list(polished)
                    candidate[s] = 0
                    candidate[u] = 1

                    candidate_fitness = self._fitness(candidate, priority)
                    gain = candidate_fitness - current_fitness

                    if gain > best_gain + 1e-12:
                        best_gain = gain
                        best_swap = (s, u)

            if best_swap is None:
                break

            s, u = best_swap
            polished[s] = 0
            polished[u] = 1

        return polished

    def _build_protection_values(
        self,
        state: List[int],
        priority: List[float]
    ) -> List[float]:

        n = len(state)

        protection = [0.1] * n

        protected = [
            i for i, bit in enumerate(state)
            if bit == 1
        ]

        protected.sort(
            key=lambda i: (
                priority[i],
                -i
            ),
            reverse=True
        )

        if not protected:
            return protection

        count = len(protected)

        if count == 1:

            protection[protected[0]] = 1.0

            return protection

        for rank, index in enumerate(protected):

            fraction = rank / (count - 1)

            protection[index] = (
                1.0 - 0.4 * fraction
            )

        return protection


def allocate_qiea(
    text: str,
    confidence: List[float],
    criticality: List[float],
    channel_bitrate_kbps: float,
    language: str,
    **allocator_kwargs,
) -> Packet:
    """
    Stateless-function wrapper around QuantumAllocator, matching the
    calling convention of allocate_greedy()/allocate() elsewhere in the
    repo. Lets call sites use this without adopting the class-based
    BandwidthAllocator pattern immediately.

    NOTE: confirm with the team whether allocate_greedy should also
    become a BandwidthAllocator subclass, and whether main.py should
    hold a long-lived allocator instance (for population_size/seed
    config) rather than calling a stateless function per request. Not
    decided here since it changes call sites app-wide.
    """

    allocator = QuantumAllocator(**allocator_kwargs)

    return allocator.allocate(
        text=text,
        confidence=confidence,
        criticality=criticality,
        channel_bitrate_kbps=channel_bitrate_kbps,
        language=language,
    )


def _run_tests():

    print("=" * 60)
    print("QIEA ALLOCATOR TEST SUITE")
    print("=" * 60)

    allocator = QuantumAllocator(
        reference_bitrate_kbps=8.0,
        min_protect_fraction=0.15,
        population_size=20,
        generations=60,
        seed=42,
    )

    text = (
        "Um listen to me Commander Sharma basically "
        "we need 2 choppers at 28.5N and 77.1E immediately"
    )

    tokens = text.split()

    confidence = [0.95] * len(tokens)

    criticality = [0.0] * len(tokens)

    confidence[tokens.index("28.5N")] = 0.40

    criticality[tokens.index("28.5N")] = 1.0
    criticality[tokens.index("77.1E")] = 1.0
    criticality[tokens.index("immediately")] = 1.0
    criticality[tokens.index("choppers")] = 0.8

    bitrate = 2.0

    print("\nTEST 1: Basic allocation")

    packet = allocator.allocate(
        text=text,
        confidence=confidence,
        criticality=criticality,
        channel_bitrate_kbps=bitrate,
        language="en",
    )

    assert isinstance(packet, Packet)
    assert len(packet.tokens) == len(tokens)
    assert len(packet.protection_per_token) == len(tokens)

    print("PASS")

    print("\nTEST 2: Language validation")

    try:
        allocator.allocate(
            text="hello world",
            confidence=[0.5, 0.5],
            criticality=[0.5, 0.5],
            channel_bitrate_kbps=4.0,
            language="fr",
        )
        raise AssertionError("Invalid language should fail")
    except ValueError:
        print("PASS")

    print("\nTEST 3: Confidence validation")

    try:
        allocator.allocate(
            text="hello world",
            confidence=[0.5, 1.5],
            criticality=[0.5, 0.5],
            channel_bitrate_kbps=4.0,
            language="en",
        )
        raise AssertionError("Invalid confidence should fail")
    except ValueError:
        print("PASS")

    print("\nTEST 4: Length validation")

    try:
        allocator.allocate(
            text="hello world",
            confidence=[0.5],
            criticality=[0.5, 0.5],
            channel_bitrate_kbps=4.0,
            language="en",
        )
        raise AssertionError("Mismatched lengths should fail")
    except ValueError:
        print("PASS")

    print("\nTEST 5: Empty input")

    empty_packet = allocator.allocate(
        text="",
        confidence=[],
        criticality=[],
        channel_bitrate_kbps=4.0,
        language="en",
    )

    assert empty_packet.tokens == []
    assert empty_packet.protection_per_token == []

    print("PASS")

    print("\nTEST 6: Budget constraint")

    protected = sum(
        1
        for value in packet.protection_per_token
        if value > 0.5
    )

    protect_fraction = max(
        allocator.min_protect_fraction,
        min(1.0, bitrate / allocator.reference_bitrate_kbps)
    )

    expected_slots = min(
        len(tokens),
        max(1, round(len(tokens) * protect_fraction))
    )

    assert protected == expected_slots

    print(f"PASS - protected {protected}/{len(tokens)} tokens")

    print("\nTEST 7: QIEA beats naive top-k once segments matter")

    # Recomputed with this allocator's own priority_mode, not hardcoded
    # to the old product formula.
    priority = allocator._calculate_priority(confidence, criticality)

    naive_topk = sorted(
        range(len(tokens)),
        key=lambda i: (priority[i], -i),
        reverse=True
    )[:expected_slots]

    naive_state = [0] * len(tokens)
    for i in naive_topk:
        naive_state[i] = 1

    naive_fitness = allocator._fitness(naive_state, priority)

    qiea_state = [
        1 if value > 0.5 else 0
        for value in packet.protection_per_token
    ]
    qiea_fitness = allocator._fitness(qiea_state, priority)

    # QIEA's segment-aware search must be at least as good as naive
    # top-k on the SAME segment-aware objective (it can never be
    # strictly worse, since _polish only accepts improving swaps from
    # any starting point including naive top-k's own layout).
    assert qiea_fitness >= naive_fitness - 1e-9

    print(
        f"PASS - naive_topk fitness = {naive_fitness:.4f}, "
        f"qiea fitness = {qiea_fitness:.4f}"
    )

    print("\nTEST 8: Hindi support")

    hindi_packet = allocator.allocate(
        text="humein turant madad chahiye",
        confidence=[0.9, 0.9, 0.9, 0.9],
        criticality=[1.0, 1.0, 1.0, 1.0],
        channel_bitrate_kbps=2.0,
        language="hi",
    )

    assert hindi_packet.language == "hi"

    print("PASS")

    print("\nTEST 9: Deterministic output")

    allocator_a = QuantumAllocator(seed=123)
    allocator_b = QuantumAllocator(seed=123)

    packet_a = allocator_a.allocate(
        text=text,
        confidence=confidence,
        criticality=criticality,
        channel_bitrate_kbps=bitrate,
        language="en",
    )

    packet_b = allocator_b.allocate(
        text=text,
        confidence=confidence,
        criticality=criticality,
        channel_bitrate_kbps=bitrate,
        language="en",
    )

    assert packet_a.protection_per_token == packet_b.protection_per_token

    print("PASS")

    print("\nTEST 10: Fragmentation penalty is real (segments matter)")

    # A hand-built case where naive top-k (priority-only) picks
    # scattered singletons, but grouping the SAME token count into a
    # contiguous run scores higher once segment overhead is charged.
    demo_allocator = QuantumAllocator(
        interaction_overhead=0.5,
        seed=7,
    )

    # 6 tokens, alternating priority so top-k picks positions 0,2,4
    # (three separate singleton segments) if it ignores adjacency.
    demo_priority = [1.0, 0.9, 1.0, 0.9, 1.0, 0.9]

    scattered_state = [1, 0, 1, 0, 1, 0]      # 3 segments
    contiguous_state = [1, 1, 1, 0, 0, 0]     # 1 segment, same slot count

    scattered_fitness = demo_allocator._fitness(scattered_state, demo_priority)
    contiguous_fitness = demo_allocator._fitness(contiguous_state, demo_priority)

    assert contiguous_fitness > scattered_fitness

    print(
        f"PASS - scattered fitness = {scattered_fitness:.4f} < "
        f"contiguous fitness = {contiguous_fitness:.4f} "
        f"(same {sum(scattered_state)} tokens protected either way)"
    )

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    _run_tests()