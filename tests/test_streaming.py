"""A dataset is an address space. These are the properties that buys.

The failure this replaces was concrete: the generator was lazy, and then
``load_data`` called ``list()`` on it and the sampler shuffled an index array
over the whole corpus. So the practical ceiling on a training set was RAM, and
the size of a split was a memory cost rather than a number.
"""

from __future__ import annotations

import tracemalloc

import pytest

from symbolic_ai_core.data.case import case_from_episode, language_episode_view
from symbolic_ai_core.data.curriculum import episode_at, generate, lesson_ids
from symbolic_ai_core.data.dataset import CurriculumDataset, SplitSpec
from symbolic_ai_core.data.key import (SampleKey, block_permutation, keyed_seed,
                                       positions)
from symbolic_ai_core.data.stream import Cursor, stream_episodes


@pytest.fixture(scope="module")
def small():
    return CurriculumDataset(lessons=lesson_ids()[:6], dataset_id="test")


# --- the permutation ------------------------------------------------------
@pytest.mark.parametrize("domain", [1, 2, 7, 64, 100, 179 * 16, 999983])
def test_block_permutation_is_a_bijection(domain):
    if domain > 1000:                       # spot-check the big ones
        seen = {block_permutation(i, domain, 42) for i in range(0, domain, 997)}
        assert len(seen) == len(range(0, domain, 997))
        assert all(0 <= v < domain for v in seen)
        return
    out = [block_permutation(i, domain, 42) for i in range(domain)]
    assert sorted(out) == list(range(domain)), (
        "a shuffled epoch must see every index exactly once")


def test_the_permutation_shuffles():
    n = 512
    out = [block_permutation(i, n, 7) for i in range(n)]
    assert sum(a == b for a, b in zip(out, range(n))) < n // 8


def test_keyed_seed_is_stable_across_processes():
    """`hash()` is salted per process; a resumed run would reshuffle."""
    assert keyed_seed("a", "b", 3) == keyed_seed("a", "b", 3)
    assert keyed_seed("a", "b", 3) != keyed_seed("a", "b", 4)


def test_worker_shards_disjoint():
    block, workers = 4096, 7
    shards = [list(positions(block=block, epoch=0, worker=w, workers=workers,
                             key=99)) for w in range(workers)]
    flat = [x for s in shards for x in s]
    assert len(flat) == block
    assert len(set(flat)) == block, "two workers drew the same ordinal"
    assert sorted(flat) == list(range(block)), "a shard was lost"


def test_an_epoch_draws_new_samples_not_the_same_ones_reshuffled():
    a = set(positions(block=64, epoch=0, worker=0, workers=1, key=5))
    b = set(positions(block=64, epoch=1, worker=0, workers=1, key=5))
    assert a.isdisjoint(b)


def test_an_invalid_shard_is_refused():
    with pytest.raises(ValueError):
        list(positions(block=8, epoch=0, worker=3, workers=3, key=1))[:1]
    with pytest.raises(ValueError):
        list(positions(block=8, epoch=0, worker=-1, workers=3, key=1))[:1]


# --- the address space ----------------------------------------------------
def test_virtual_dataset_constant_memory(small):
    """A trillion-address split costs the same as a tiny one."""
    tiny = CurriculumDataset(lessons=small.lessons, dataset_id="tiny",
                             splits={"train": SplitSpec(seed0=0, per_lesson=4)})
    huge = CurriculumDataset(lessons=small.lessons, dataset_id="huge",
                             splits={"train": SplitSpec(seed0=0,
                                                        per_lesson=10 ** 12)})
    assert huge.block("train") == len(small.lessons) * 10 ** 12

    def peak(ds):
        tracemalloc.start()
        for _, _ in zip(range(20), ds.keys("train")):
            pass
        cur, top = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return top

    a, b = peak(tiny), peak(huge)
    assert b < a + 200_000, (
        f"a 10^12-address split cost {b - a} more bytes than a 24-address one; "
        f"something is materialising the index")


def test_sample_key_exact_replay(small):
    key = SampleKey("test", "train", 0, 137)
    a, b = small.get(key), small.get(key)
    assert a.to_dict() == b.to_dict()


def test_the_address_maps_to_a_lesson_and_a_seed(small):
    """Lesson-minor: any prefix covers every lesson."""
    got = [small.address("train", i)[0] for i in range(len(small.lessons))]
    assert sorted(got) == sorted(small.lessons)
    assert small.address("train", 0)[1] == small.address("train", 1)[1]
    assert small.address("train", len(small.lessons))[1] == 1


def test_train_and_eval_addresses_cannot_meet(small):
    train_seeds = {small.address("train", i)[1] for i in range(2000)}
    eval_seeds = {small.address("eval", i)[1]
                  for i in range(small.block("eval"))}
    assert train_seeds.isdisjoint(eval_seeds)
    assert min(eval_seeds) >= 1_000_000


def test_a_finite_split_refuses_a_second_epoch(small):
    with pytest.raises(ValueError, match="finite and pinned"):
        next(small.keys("eval", epoch=1))


def test_the_eval_split_is_pinned_and_unshuffled(small):
    ks = [k.ordinal for k in small.keys("eval")]
    assert ks == list(range(small.block("eval")))


# --- equivalence with the old path ---------------------------------------
def test_the_streaming_path_produces_the_old_episodes(small):
    """`episode_at` is what `generate` iterates. Byte-identical, or the
    fingerprint -- and every published number resting on it -- has moved."""
    lids = list(small.lessons)[:3]
    listed = [e.to_dict() for e in generate(lids, n=2, seed0=0)]
    addressed = [episode_at(l, s).to_dict() for l in lids for s in (0, 1)]
    assert listed == addressed


def test_old_episode_compatibility(small):
    """A case round-trips to the exact Episode the trainer already reads."""
    key = SampleKey("test", "train", 0, 5)
    ep = small.episode(key)
    case = case_from_episode(ep, key)
    assert language_episode_view(case).to_dict() == ep.to_dict()


def test_one_case_carries_several_surfaces(small):
    case = small.get(SampleKey("test", "train", 0, 11))
    assert case.surfaces() == ("term_graph", "text")
    assert case.world is not None and case.world.type == "term_graph"
    assert set(case.queries) == {"prompt", "choices"}
    assert set(case.targets) == {"answer"}
    assert case.observations["text"].profiles == ("language.document",)


# --- the stream -----------------------------------------------------------
def test_an_interrupted_stream_resumes_at_the_same_next_key(small):
    c1 = Cursor("train")
    first = [e.instance_id
             for _, e in zip(range(6), stream_episodes(small, c1, epochs=None))]
    assert c1.consumed == 6

    resumed = Cursor.from_dict(c1.to_dict())
    nxt = [e.instance_id
           for _, e in zip(range(3), stream_episodes(small, resumed,
                                                     epochs=None))]
    straight = [e.instance_id
                for _, e in zip(range(9),
                                stream_episodes(small, Cursor("train"),
                                                epochs=None))]
    assert first + nxt == straight


def test_a_finite_split_stops(small):
    c = Cursor("eval")
    got = list(stream_episodes(small, c, epochs=None))
    assert len(got) == small.block("eval")


def test_workers_stream_disjoint_samples(small):
    seen = []
    for w in range(3):
        c = Cursor("train", worker=w, workers=3)
        seen.append({e.instance_id
                     for _, e in zip(range(8), stream_episodes(small, c,
                                                               epochs=None))})
    assert not (seen[0] & seen[1]) and not (seen[1] & seen[2])
    assert not (seen[0] & seen[2])
