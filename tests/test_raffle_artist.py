import importlib.util
import copy
from pathlib import Path
import random
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("raffle_artist_tests")
package.__path__ = [str(ROOT)]
spec = importlib.util.spec_from_file_location("raffle_artist_tests.raffle_artist", ROOT / "raffle_artist.py")
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
    "raffle_artist_tests": package,
    "folder_paths": types.ModuleType("folder_paths"),
}):
    spec.loader.exec_module(module)


ARTISTS = [
    {"tag": "zeta_artist", "source": "theta", "works": 100, "uniqueness_score": 70},
    {"tag": "beta_artist", "source": "theta", "works": 900, "uniqueness_score": 10},
    {"trigger": "alpha artist", "source_kind": "artist", "works": 20, "uniqueness_score": 90},
    {"trigger": "delta_artist", "source_kind": "artist", "works": 100, "uniqueness_score": 40},
    {"trigger": "epsilon artist", "source_kind": "artist", "works": 300, "uniqueness_score": 10},
    {"trigger": "gamma artist", "source_kind": "artist", "works": 5, "uniqueness_score": 80},
    {"trigger": "eta_artist", "source_kind": "artist", "works": 50, "uniqueness_score": 60},
    {"trigger": "@Alpha_artist", "source_kind": "artist"},
    {"trigger": "not an artist, touhou", "tags": ["1girl"], "source_kind": "character"},
    {"tag": "@@beta artist"},
    {"tag": ""},
]
EXPECTED = ["alpha_artist", "beta_artist", "delta_artist", "epsilon_artist", "eta_artist", "gamma_artist", "zeta_artist"]


class RaffleArtistTests(unittest.TestCase):
    def setUp(self):
        self.node = module.RaffleArtist()
        source_patch = patch.object(module.artist_data, "load", return_value=ARTISTS)
        self.source = source_patch.start()
        self.addCleanup(source_patch.stop)

    def test_interface_has_only_widgets_and_three_raffle_outputs(self):
        schema = self.node.INPUT_TYPES()
        self.assertEqual(set(schema), {"required"})
        self.assertEqual(list(schema["required"]), [
            "seed", "mode", "artist_count", "tag_form", "sort_by", "sort_order", "shuffle_seed",
        ])
        self.assertTrue(schema["required"]["seed"][1]["control_after_generate"])
        self.assertEqual(schema["required"]["mode"][0], ["Random", "Sequential"])
        self.assertEqual(schema["required"]["mode"][1]["default"], "Random")
        self.assertEqual(schema["required"]["artist_count"], ("INT", {"default": 1, "min": 1, "max": 6}))
        self.assertEqual(schema["required"]["tag_form"][1]["default"], "Anima")
        self.assertEqual(schema["required"]["sort_by"][0], ["Popularity", "Uniqueness", "A–Z", "Shuffle"])
        self.assertEqual(schema["required"]["sort_by"][1]["default"], "A–Z")
        self.assertEqual(schema["required"]["sort_order"][0], ["Ascending", "Descending"])
        self.assertEqual(schema["required"]["sort_order"][1]["default"], "Ascending")
        self.assertEqual(schema["required"]["shuffle_seed"][1]["default"], 0)
        self.assertFalse(schema["required"]["shuffle_seed"][1]["control_after_generate"])
        self.assertEqual(self.node.RETURN_TYPES, ("STRING",) * 3)
        self.assertEqual(self.node.RETURN_NAMES, ("Raffled output", "Unfiltered", "Debug info"))

    def test_pool_excludes_characters_empty_names_and_duplicate_artists(self):
        self.assertEqual(module._artist_pool(), EXPECTED)
        self.source.assert_called_once_with()

    def test_random_samples_one_to_six_unique_artists_with_no_character_tags(self):
        for count in range(1, 7):
            with self.subTest(count=count):
                output, unfiltered, debug = self.node.process_tags(seed=123, artist_count=count, tag_form="SD")
                tags = output.split(", ")
                self.assertEqual(len(tags), count)
                self.assertEqual(len(set(tags)), count)
                self.assertTrue(set(tags) <= set(EXPECTED))
                self.assertEqual(unfiltered, output)
                self.assertIn("Artist pool size: 7", debug)
                self.assertIn(f"Artist count: {count}", debug)

    def test_random_seed_is_repeatable_and_does_not_change_global_random_state(self):
        state = random.getstate()
        first = self.node.process_tags(seed=123, artist_count=6)
        self.assertEqual(first, module.RaffleArtist().process_tags(seed=123, artist_count=6))
        self.assertEqual(state, random.getstate())
        self.assertNotEqual(first[0], self.node.process_tags(seed=124, artist_count=6)[0])

    def test_tag_form_changes_format_without_changing_selection(self):
        for mode in ("Random", "Sequential"):
            for sort_by in ("Popularity", "Uniqueness", "A–Z", "Shuffle"):
                for sort_order in ("Ascending", "Descending"):
                    with self.subTest(mode=mode, sort_by=sort_by, sort_order=sort_order):
                        kwargs = dict(seed=2, artist_count=6, mode=mode, sort_by=sort_by, sort_order=sort_order)
                        anima = self.node.process_tags(**kwargs)
                        sd = self.node.process_tags(**kwargs, tag_form="SD")
                        self.assertEqual(anima[0], ", ".join("@" + tag.replace("_", " ") for tag in sd[0].split(", ")))
                        self.assertEqual(anima[1], anima[0])
                        self.assertEqual(sd[1], sd[0])
                        self.assertEqual(anima[2], sd[2])

    def test_sequential_mode_advances_whole_batches_and_wraps(self):
        for seed in (0, 1, 2, 3, 4, 99, 0xffffffffffffffff):
            with self.subTest(seed=seed):
                output, _, _ = self.node.process_tags(seed=seed, mode="Sequential", artist_count=2, tag_form="SD")
                self.assertEqual(output.split(", "), [EXPECTED[(seed * 2 + index) % 7] for index in range(2)])

    def test_sequential_selection_has_no_hidden_cursor_and_ignores_source_order(self):
        kwargs = dict(seed=2, mode="Sequential", artist_count=3)
        first = self.node.process_tags(**kwargs)
        self.node.process_tags(seed=100, mode="Sequential")
        self.source.return_value = list(reversed(ARTISTS[:7]))
        self.assertEqual(first, module.RaffleArtist().process_tags(**kwargs))

    def test_existing_at_prefixes_are_not_repeated(self):
        self.source.return_value = [{"trigger": " @@some artist  ", "source_kind": "artist"}]
        self.assertEqual(self.node.process_tags()[0], "@some artist")
        self.assertEqual(self.node.process_tags(tag_form="SD")[0], "some_artist")

    def test_escaped_parentheses_do_not_create_duplicate_artists(self):
        self.source.return_value = [{"tag": r"artist_\(circle\)"}, {"trigger": "artist (circle)"}]
        output, _, debug = self.node.process_tags()
        self.assertEqual(output, r"@artist \(circle\)")
        self.assertIn("Artist pool size: 1", debug)

    def test_numeric_sorting_in_both_directions_keeps_ties_in_name_order(self):
        orders = {
            ("Popularity", "Ascending"): ["gamma", "alpha", "eta", "delta", "zeta", "epsilon", "beta"],
            ("Popularity", "Descending"): ["beta", "epsilon", "delta", "zeta", "eta", "alpha", "gamma"],
            ("Uniqueness", "Ascending"): ["beta", "epsilon", "delta", "eta", "zeta", "gamma", "alpha"],
            ("Uniqueness", "Descending"): ["alpha", "gamma", "zeta", "eta", "delta", "beta", "epsilon"],
        }
        for (sort_by, sort_order), expected in orders.items():
            actual = []
            for seed in range(7):
                with self.subTest(sort_by=sort_by, sort_order=sort_order, seed=seed):
                    output, unfiltered, debug = self.node.process_tags(
                        seed=seed, mode="Sequential", tag_form="SD", sort_by=sort_by, sort_order=sort_order,
                    )
                    actual.append(output)
                    self.assertEqual(output, unfiltered)
                    self.assertIn(f"Sort by: {sort_by}\nSort order: {sort_order}", debug)
            self.assertEqual(actual, [name + "_artist" for name in expected])

    def test_name_descending_is_the_reverse_of_existing_default(self):
        actual = [self.node.process_tags(seed=seed, mode="Sequential", tag_form="SD", sort_order="Descending")[0]
                  for seed in range(7)]
        self.assertEqual(actual, list(reversed(EXPECTED)))

    def test_metrics_are_numeric_and_missing_values_stay_last_in_both_directions(self):
        for sort_by, field in (("Popularity", "works"), ("Uniqueness", "uniqueness_score")):
            self.source.return_value = [
                {"tag": "zero", field: 0}, {"tag": "two", field: "2"}, {"tag": "ten", field: "10"},
                {"tag": "missing"}, {"tag": "none", field: None}, {"tag": "bad", field: "invalid"},
                {"tag": "nan", field: float("nan")}, {"tag": "infinite", field: float("inf")},
            ]
            missing = ["bad", "infinite", "missing", "nan", "none"]
            for order, valid in (("Ascending", ["zero", "two", "ten"]), ("Descending", ["ten", "two", "zero"])):
                with self.subTest(sort_by=sort_by, sort_order=order):
                    self.assertEqual(module._artist_pool(sort_by, order), valid + missing)

    def test_official_missing_score_is_not_treated_as_a_valid_zero_score(self):
        self.source.return_value = [
            {"tag": "unscored", "source": "animadex", "score": None, "uniqueness_score": 0},
            {"tag": "zero", "score": 0, "uniqueness_score": 0},
            {"tag": "high", "score": 0.8, "uniqueness_score": 80},
        ]
        self.assertEqual(module._artist_pool("Uniqueness", "Ascending"), ["zero", "high", "unscored"])
        self.assertEqual(module._artist_pool("Uniqueness", "Descending"), ["high", "zero", "unscored"])

    def test_shuffle_is_reproducible_and_uses_its_own_seed(self):
        state = random.getstate()
        first = module._artist_pool("Shuffle", shuffle_seed=7)
        self.assertEqual(first, module._artist_pool("Shuffle", shuffle_seed=7))
        self.assertNotEqual(first, module._artist_pool("Shuffle", shuffle_seed=8))
        self.assertCountEqual(first, EXPECTED)
        self.assertEqual(state, random.getstate())

    def test_shuffle_descending_reverses_the_same_fixed_permutation(self):
        ascending = [self.node.process_tags(seed=seed, mode="Sequential", tag_form="SD",
                                            sort_by="Shuffle", shuffle_seed=7)[0] for seed in range(7)]
        descending = [self.node.process_tags(seed=seed, mode="Sequential", tag_form="SD", sort_by="Shuffle",
                                             sort_order="Descending", shuffle_seed=7)[0] for seed in range(7)]
        self.assertEqual(descending, list(reversed(ascending)))
        self.assertCountEqual(ascending, EXPECTED)

    def test_shuffle_traverses_consecutive_batches_before_wrapping(self):
        for order in ("Ascending", "Descending"):
            kwargs = dict(mode="Sequential", tag_form="SD", sort_by="Shuffle", sort_order=order, shuffle_seed=7)
            single = [self.node.process_tags(seed=seed, **kwargs)[0] for seed in range(7)]
            batches = []
            for seed in range(3):
                result = self.node.process_tags(seed=seed, artist_count=3, **kwargs)
                batches.extend(result[0].split(", "))
                self.assertIn("Shuffle seed: 7", result[2])
            self.assertEqual(batches, single + single[:2])
            self.assertEqual(len(set(batches[:7])), 7)

    def test_random_mode_ignores_sequential_sorting_controls(self):
        baseline = self.node.process_tags(seed=123, artist_count=6)
        for sort_by in ("Popularity", "Uniqueness", "A–Z", "Shuffle"):
            for order in ("Ascending", "Descending"):
                with self.subTest(sort_by=sort_by, order=order):
                    self.assertEqual(baseline, self.node.process_tags(seed=123, artist_count=6,
                        sort_by=sort_by, sort_order=order, shuffle_seed=999))

    def test_sorting_does_not_mutate_the_shared_source_records(self):
        original = copy.deepcopy(ARTISTS)
        for sort_by in ("Popularity", "Uniqueness", "A–Z", "Shuffle"):
            for order in ("Ascending", "Descending"):
                self.node.process_tags(mode="Sequential", sort_by=sort_by, sort_order=order)
        self.assertEqual(ARTISTS, original)

    def test_empty_and_too_small_pools_do_not_fall_back_or_repeat_artists(self):
        self.source.return_value = [{"source_kind": "character", "trigger": "girl, touhou"}]
        with self.assertRaisesRegex(ValueError, "artist index is empty"):
            self.node.process_tags()
        self.source.return_value = ARTISTS[:1]
        for mode in ("Random", "Sequential"):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "Only 1 unique artists"):
                self.node.process_tags(mode=mode, artist_count=2)

    def test_invalid_options_are_rejected(self):
        for count in (0, 7, 1.5):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, "integer from 1 to 6"):
                self.node.process_tags(artist_count=count)
        with self.assertRaisesRegex(ValueError, "Unknown artist selection mode"):
            self.node.process_tags(mode="unsupported")
        with self.assertRaisesRegex(ValueError, "Unknown tag form"):
            self.node.process_tags(tag_form="unsupported")
        with self.assertRaisesRegex(ValueError, "Unknown artist sort method"):
            self.node.process_tags(sort_by="unsupported")
        with self.assertRaisesRegex(ValueError, "Unknown artist sort order"):
            self.node.process_tags(sort_order="unsupported")


if __name__ == "__main__":
    unittest.main()
