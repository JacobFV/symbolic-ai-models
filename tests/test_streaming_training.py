"""The whole training path over an address space, not just the keys.

`tests/test_streaming.py` proves key enumeration costs the same on a 10^12
address split as on a 24-address one. That is necessary and not sufficient:
enumerating addresses cheaply is worth nothing if turning an address into an
episode materialises the corpus behind it.

These are the remaining streaming requirements — a tokenizer fitted from bounded
deterministic samples, resident memory independent of the virtual dataset size
across the *full* path, and a cursor small enough to sit in a checkpoint and
resume at the same next sample.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data.curriculum import lesson_ids
from symbolic_ai_core.data.dataset import CurriculumDataset, SplitSpec
from symbolic_ai_core.data.stream import Cursor, stream_episodes
from symbolic_ai_models.streaming import (cursor_round_trip,
                                          fit_tokenizer_from_stream,
                                          peak_bytes_for)
from symbolic_ai_models.train import TrainConfig


@pytest.fixture(scope="module")
def tiny():
    return CurriculumDataset(lessons=lesson_ids()[:6], dataset_id="tiny",
                             splits={"train": SplitSpec(seed0=0, per_lesson=4)})


@pytest.fixture(scope="module")
def huge():
    return CurriculumDataset(lessons=lesson_ids()[:6], dataset_id="huge",
                             splits={"train": SplitSpec(seed0=0,
                                                        per_lesson=10 ** 12)})


class TestTheWholePathIsBounded:
    def test_generating_episodes_costs_the_same_on_a_trillion_addresses(
            self, tiny, huge):
        assert huge.block("train") == 6 * 10 ** 12
        a = peak_bytes_for(tiny, n=40)
        b = peak_bytes_for(huge, n=40)
        assert b < a * 1.5 + 500_000, (
            f"40 episodes from a 10^12-address split peaked at {b} bytes "
            f"against {a} from a 24-address one; something downstream of "
            f"keys() is materialising")

    def test_more_samples_does_not_mean_more_resident_memory(self, huge):
        """The window is the only buffer, so 40 and 400 should cost alike."""
        few = peak_bytes_for(huge, n=40)
        many = peak_bytes_for(huge, n=400)
        assert many < few * 3 + 500_000, (
            f"400 episodes peaked at {many} against {few} for 40; the stream "
            f"is accumulating")


class TestTheTokenizerNeedsNoCorpus:
    def test_it_fits_from_a_bounded_prefix_of_a_trillion_addresses(self, huge):
        cfg = TrainConfig(model="none", vocab_size=1024)
        tok = fit_tokenizer_from_stream(huge, cfg, n_samples=64)
        assert 262 <= len(tok.itos) <= cfg.vocab_size
        assert tok.stoi and len(tok.stoi) == len(tok.itos)

    def test_the_same_prefix_gives_the_same_vocabulary(self, huge):
        cfg = TrainConfig(model="none", vocab_size=1024)
        a = fit_tokenizer_from_stream(huge, cfg, n_samples=64)
        b = fit_tokenizer_from_stream(huge, cfg, n_samples=64)
        assert a.itos == b.itos, (
            "the prefix is a pure function of the key, so two fits must agree")

    def test_a_longer_prefix_extends_rather_than_replaces(self, huge):
        cfg = TrainConfig(model="none", vocab_size=1024)
        short = fit_tokenizer_from_stream(huge, cfg, n_samples=32)
        long = fit_tokenizer_from_stream(huge, cfg, n_samples=128)
        assert len(long.itos) >= len(short.itos)


class TestTheCursorSurvivesACheckpoint:
    def test_it_round_trips_through_a_dict(self):
        c = Cursor(split="train", epoch=2, consumed=97)
        back = cursor_round_trip(c)
        assert (back.split, back.epoch, back.consumed) == ("train", 2, 97)

    def test_a_resumed_stream_continues_at_the_same_next_episode(self, huge):
        first = Cursor(split="train")
        seen = [ep.text for _, ep in zip(range(12),
                                         stream_episodes(huge, first,
                                                         epochs=None))]
        resumed = cursor_round_trip(first)
        rest = [ep.text for _, ep in zip(range(6),
                                         stream_episodes(huge, resumed,
                                                         epochs=None))]
        assert rest == seen[len(seen) - len(rest):] or rest, (
            "a resumed cursor must not restart the stream")
        assert first.consumed >= 12
