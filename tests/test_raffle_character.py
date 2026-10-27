import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("raffle_character_tests")
package.__path__ = [str(ROOT)]
spec = importlib.util.spec_from_file_location("raffle_character_tests.raffle_character", ROOT / "raffle_character.py")
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
    "raffle_character_tests": package,
    "folder_paths": types.ModuleType("folder_paths"),
}):
    spec.loader.exec_module(module)


CHARACTERS = [
    {"trigger": "alice, touhou", "tags": ["1girl", "blue eyes", "long hair", "^_^", "o_o"]},
    {"trigger": "reimu, touhou", "tags": ["1girl", "red eyes"]},
    {"trigger": "other girl, other series", "tags": ["1girl", "blue_eyes"]},
    {"trigger": "hero, touhou", "tags": ["1boy", "blue eyes"]},
    {"trigger": "robot, original", "tags": ["metal body"]},
    {"trigger": "duo, original", "tags": ["1girl", "1boy"]},
    {"trigger": "trigger girl, series, 1girl", "tags": ["green eyes"]},
]


class RaffleCharacterTests(unittest.TestCase):
    def setUp(self):
        self.node = module.RaffleCharacter()
        source_patch = patch.object(module.artist_data, "load_animadex", return_value=CHARACTERS)
        self.source = source_patch.start()
        self.addCleanup(source_patch.stop)

    def test_widgets_and_outputs_match_requested_interface(self):
        schema = self.node.INPUT_TYPES()
        self.assertEqual(set(schema), {"required"})
        self.assertEqual(set(schema["required"]), {
            "seed", "taglists_must_include", "filter_out_tags", "tag_form", "character_sex",
            "output_mode", "top_n", "character_count",
        })
        self.assertEqual(schema["required"]["taglists_must_include"][1]["default"], "")
        self.assertEqual(schema["required"]["filter_out_tags"][1]["default"], "")
        self.assertEqual(schema["required"]["character_sex"][1]["default"], "Female")
        self.assertEqual(schema["required"]["character_sex"][0], [
            "Female", "Male", "Others", "Female+Male", "Female+Others", "Female+Male+Others",
        ])
        self.assertEqual(schema["required"]["tag_form"][1]["default"], "Anima")
        self.assertEqual(schema["required"]["output_mode"][0], ["trigger+tags", "trigger"])
        self.assertEqual(schema["required"]["output_mode"][1]["default"], "trigger+tags")
        self.assertEqual(list(schema["required"])[-3:], ["output_mode", "top_n", "character_count"])
        self.assertEqual(schema["required"]["top_n"][1]["default"], 0)
        self.assertEqual(schema["required"]["top_n"][1]["min"], 0)
        self.assertEqual(schema["required"]["character_count"][1]["default"], 1)
        self.assertEqual(schema["required"]["character_count"][1]["min"], 1)
        self.assertEqual(self.node.RETURN_NAMES, ("Raffled output", "Unfiltered", "Debug info"))

    def test_all_required_tags_match_trigger_and_descriptions(self):
        output, unfiltered, debug = self.node.process_tags(taglists_must_include="touhou, blue eyes")
        self.assertEqual(output, "alice, touhou, 1girl, blue eyes, long hair, ^_^, o_o")
        self.assertEqual(unfiltered, output)
        self.assertIn("Matching character pool size: 1", debug)
        self.source.assert_called_once_with("character")

    def test_exclusions_remove_whole_characters_and_accept_space_tags(self):
        output, _, debug = self.node.process_tags(taglists_must_include="touhou", filter_out_tags="long hair, green eyes")
        self.assertEqual(output, "reimu, touhou, 1girl, red eyes")
        self.assertIn("Matching character pool size: 1", debug)

    def test_empty_filters_draw_only_the_selected_sex(self):
        for sex, expected_pool in [("Female", 4), ("Male", 1), ("Others", 2)]:
            for seed in range(8):
                with self.subTest(sex=sex, seed=seed):
                    output, unfiltered, debug = self.node.process_tags(seed=seed, character_sex=sex)
                    self.assertEqual(output, unfiltered)
                    self.assertIn(f"Matching character pool size: {expected_pool}", debug)
                    if sex == "Male":
                        self.assertTrue(output.startswith("hero, touhou"))
                    elif sex == "Others":
                        self.assertTrue(output.startswith(("robot, original", "duo, original")))
                    else:
                        self.assertFalse(output.startswith(("hero", "robot", "duo")))

    def test_seed_repeatability_and_tag_forms_preserve_selection_and_faces(self):
        kwargs = dict(seed=123, taglists_must_include="touhou, blue eyes")
        anima = self.node.process_tags(**kwargs)
        self.assertEqual(anima, self.node.process_tags(**kwargs))
        sd = self.node.process_tags(**kwargs, tag_form="SD")
        self.assertEqual(sd[0], "alice, touhou, 1girl, blue_eyes, long_hair, ^_^, o_o")
        self.assertEqual(sd[1], sd[0])
        self.assertEqual(sd[2], anima[2])

    def test_case_underscores_newlines_and_parentheses_match_exact_tags(self):
        spaced = self.node.process_tags(taglists_must_include="TOUHOU\nBlue_Eyes")
        self.assertTrue(spaced[0].startswith("alice, touhou"))
        with self.assertRaisesRegex(ValueError, "No matching"):
            self.node.process_tags(taglists_must_include="blue")
        self.source.return_value = [{"trigger": r"hero\(series\), copyright", "tags": ["1girl", "blue eyes"]}]
        output, _, _ = self.node.process_tags(taglists_must_include="hero(series)")
        self.assertIn("hero", output)

    def test_emoticon_exclusion_is_applied_before_drawing(self):
        with self.assertRaisesRegex(ValueError, "No matching"):
            self.node.process_tags(taglists_must_include="touhou, blue eyes", filter_out_tags="o_o")

    def test_trigger_only_keeps_description_filters_and_selected_character(self):
        kwargs = dict(seed=123, taglists_must_include="touhou, blue eyes", filter_out_tags="red eyes")
        complete = self.node.process_tags(**kwargs)
        trigger, unfiltered, debug = self.node.process_tags(**kwargs, output_mode="trigger")
        self.assertEqual(trigger, "alice, touhou")
        self.assertEqual(unfiltered, trigger)
        self.assertTrue(complete[0].startswith(trigger + ", "))
        self.assertIn("Matching character pool size: 1", debug)
        self.assertIn("Selected character: alice, touhou", debug)
        self.assertIn("Output mode: trigger", debug)
        with self.assertRaisesRegex(ValueError, "No matching"):
            self.node.process_tags(**{**kwargs, "filter_out_tags": "long hair"}, output_mode="trigger")

    def test_trigger_only_preserves_seed_selection_for_all_sex_pools(self):
        for sex in ("Female", "Male", "Others", "Female+Male", "Female+Others", "Female+Male+Others"):
            for seed in range(8):
                with self.subTest(sex=sex, seed=seed):
                    full = self.node.process_tags(seed=seed, character_sex=sex)
                    trigger = self.node.process_tags(seed=seed, character_sex=sex, output_mode="trigger")
                    self.assertEqual(full[2].replace("Output mode: trigger+tags", "Output mode: trigger"), trigger[2])
                    self.assertTrue(full[0].startswith(trigger[0]))

    def test_trigger_only_formats_every_trigger_tag_without_descriptions(self):
        self.source.return_value = [{"tag": "alice_margatroid, touhou, ^_^", "tags": ["1girl", "blue eyes"]}]
        kwargs = dict(taglists_must_include="blue eyes", output_mode="trigger")
        anima = self.node.process_tags(**kwargs)
        sd = self.node.process_tags(**kwargs, tag_form="SD")
        self.assertEqual(anima[:2], ("alice margatroid, touhou, ^_^",) * 2)
        self.assertEqual(sd[:2], ("alice_margatroid, touhou, ^_^",) * 2)
        self.assertEqual(anima[2], sd[2])

    def test_unknown_output_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown character output mode"):
            self.node.process_tags(output_mode="tags")

    def test_empty_source_and_conflicting_filters_do_not_fall_back(self):
        with self.assertRaisesRegex(ValueError, "No matching"):
            self.node.process_tags(taglists_must_include="touhou", filter_out_tags="touhou")
        self.source.return_value = []
        with self.assertRaisesRegex(ValueError, "character index is empty"):
            self.node.process_tags()

    def test_top_n_is_applied_after_all_tag_and_sex_filters(self):
        self.source.return_value = [
            {"trigger": "wrong series", "tags": ["1girl", "blue eyes"], "works": 9000},
            {"trigger": "male, touhou", "tags": ["1boy", "blue eyes"], "works": 8000},
            {"trigger": "excluded, touhou", "tags": ["1girl", "blue eyes", "long hair"], "works": 7000},
            {"trigger": "low, touhou", "tags": ["1girl", "blue eyes"], "works": 20},
            {"trigger": "high, touhou", "tags": ["1girl", "blue eyes"], "works": 100},
        ]
        output, unfiltered, debug = self.node.process_tags(
            taglists_must_include="touhou, blue eyes", filter_out_tags="long hair", top_n=1,
        )
        self.assertTrue(output.startswith("high, touhou"))
        self.assertEqual(output, unfiltered)
        self.assertIn("Matching character pool size: 2", debug)
        self.assertIn("Draw pool size: 1", debug)

    def test_top_ten_excludes_lower_ranked_characters(self):
        self.source.return_value = [{"trigger": f"character {index}", "tags": ["1girl"], "works": index}
                                    for index in range(15)]
        selected = {self.node.process_tags(seed=seed, top_n=10, output_mode="trigger")[0] for seed in range(100)}
        self.assertEqual(selected, {f"character {index}" for index in range(5, 15)})

    def test_zero_keeps_original_pool_order_and_seed_selection(self):
        records = [{**item, "works": index * 100} for index, item in enumerate(CHARACTERS)]
        self.source.return_value = records
        for seed in range(20):
            actual = self.node.process_tags(seed=seed, top_n=0)
            expected = module.random.Random(seed).choice([records[index] for index in (0, 1, 2, 6)])
            self.assertIn(f"Selected character: {expected['trigger']}", actual[2])
            self.assertEqual(actual, self.node.process_tags(seed=seed))
            self.assertIn("Draw pool size: 4", actual[2])

    def test_popularity_is_numeric_and_cutoff_ties_keep_source_order(self):
        self.source.return_value = [
            {"trigger": "low", "tags": ["1girl"], "works": "9"},
            {"trigger": "tie first", "tags": ["1girl"], "works": "100"},
            {"trigger": "tie second", "tags": ["1girl"], "works": 100},
            {"trigger": "missing", "tags": ["1girl"]},
        ]
        for seed in range(5):
            self.assertEqual(self.node.process_tags(seed=seed, top_n=1, output_mode="trigger")[0], "tie first")
        selected = {self.node.process_tags(seed=seed, top_n=2, output_mode="trigger")[0] for seed in range(20)}
        self.assertEqual(selected, {"tie first", "tie second"})

    def test_limit_above_pool_size_and_output_modes_preserve_selection(self):
        kwargs = dict(seed=123, top_n=100, taglists_must_include="touhou, blue eyes")
        full = self.node.process_tags(**kwargs)
        trigger = self.node.process_tags(**kwargs, output_mode="trigger")
        sd = self.node.process_tags(**kwargs, tag_form="SD")
        self.assertEqual(full, self.node.process_tags(**kwargs))
        self.assertEqual(trigger[0], "alice, touhou")
        self.assertIn("Draw pool size: 1", full[2])
        self.assertEqual(full[2], sd[2])

    def test_invalid_limits_are_rejected(self):
        for value in (-1, 1.5, "10", True):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "non-negative integer"):
                self.node.process_tags(top_n=value)

    def test_combined_sexes_draw_from_the_union_without_duplicating_or_reordering_records(self):
        indices = {
            "Female+Male": (0, 1, 2, 3, 6),
            "Female+Others": (0, 1, 2, 4, 5, 6),
            "Female+Male+Others": tuple(range(7)),
        }
        for sex, positions in indices.items():
            expected_pool = [CHARACTERS[index] for index in positions]
            selected = set()
            for seed in range(50):
                with self.subTest(sex=sex, seed=seed):
                    output, unfiltered, debug = self.node.process_tags(seed=seed, character_sex=sex, output_mode="trigger")
                    expected = module.random.Random(seed).choice(expected_pool)["trigger"]
                    self.assertEqual(output, expected)
                    self.assertEqual(output, unfiltered)
                    self.assertIn(f"Matching character pool size: {len(positions)}", debug)
                    selected.add(output)
            self.assertEqual(selected, {item["trigger"] for item in expected_pool})

    def test_combined_sexes_still_apply_include_and_exclude_tags(self):
        for sex in ("Female+Male", "Female+Male+Others"):
            output, _, debug = self.node.process_tags(character_sex=sex, taglists_must_include="touhou, blue eyes",
                                                      filter_out_tags="long hair", output_mode="trigger")
            self.assertEqual(output, "hero, touhou")
            self.assertIn("Matching character pool size: 1", debug)
        with self.assertRaisesRegex(ValueError, "No matching Female\\+Others"):
            self.node.process_tags(character_sex="Female+Others", taglists_must_include="touhou, blue eyes",
                                   filter_out_tags="long hair")
        output, _, _ = self.node.process_tags(character_sex="Female+Others", taglists_must_include="original",
                                              filter_out_tags="metal body", output_mode="trigger")
        self.assertEqual(output, "duo, original")

    def test_top_n_ranks_the_whole_merged_pool_instead_of_each_sex_separately(self):
        self.source.return_value = [
            {"trigger": "girl", "tags": ["1girl", "blue eyes"], "works": 30},
            {"trigger": "boy", "tags": ["1boy", "blue eyes"], "works": 100},
            {"trigger": "robot", "tags": ["blue eyes"], "works": 60},
            {"trigger": "excluded", "tags": ["1boy", "red eyes"], "works": 1000},
        ]
        kwargs = dict(taglists_must_include="blue eyes", output_mode="trigger", top_n=1)
        for sex, expected in (("Female+Male", "boy"), ("Female+Others", "robot"), ("Female+Male+Others", "boy")):
            for seed in range(5):
                self.assertEqual(self.node.process_tags(seed=seed, character_sex=sex, **kwargs)[0], expected)
        selected = set()
        for seed in range(20):
            output, _, debug = self.node.process_tags(seed=seed, character_sex="Female+Male+Others", **{**kwargs, "top_n": 2})
            selected.add(output)
            self.assertIn("Matching character pool size: 3", debug)
            self.assertIn("Draw pool size: 2", debug)
        self.assertEqual(selected, {"boy", "robot"})

    def test_combined_sex_validation_preserves_case_insensitive_matching(self):
        actual = self.node.process_tags(character_sex=" female+MALE ", output_mode="trigger")
        expected = self.node.process_tags(character_sex="Female+Male", output_mode="trigger")
        self.assertEqual(actual[:2], expected[:2])
        for sex in ("", "Female+unknown", "Female+Male+unknown", "Male+Others"):
            with self.subTest(sex=sex), self.assertRaisesRegex(ValueError, "Unknown Character Sex"):
                self.node.process_tags(character_sex=sex)

    def test_multiple_characters_are_distinct_repeatable_and_do_not_change_global_random_state(self):
        state = module.random.getstate()
        kwargs = dict(seed=123, character_sex="Female+Male+Others", character_count=3, output_mode="trigger")
        result = self.node.process_tags(**kwargs)
        chosen = [line.removeprefix("Selected character: ") for line in result[2].splitlines()
                  if line.startswith("Selected character: ")]
        self.assertEqual(len(chosen), 3)
        self.assertEqual(len(set(chosen)), 3)
        self.assertTrue(set(chosen) <= {item["trigger"] for item in CHARACTERS})
        self.assertEqual(result[:2], (", ".join(chosen),) * 2)
        self.assertEqual(result, self.node.process_tags(**kwargs))
        self.assertEqual(state, module.random.getstate())
        self.assertIn("Character count: 3", result[2])

    def test_count_is_applied_after_merged_sex_tag_filters_and_top_n(self):
        self.source.return_value = [
            {"trigger": "girl, touhou", "tags": ["1girl", "blue eyes"], "works": 80},
            {"trigger": "boy, touhou", "tags": ["1boy", "blue eyes"], "works": 100},
            {"trigger": "robot, touhou", "tags": ["blue eyes"], "works": 60},
            {"trigger": "excluded, touhou", "tags": ["1girl", "blue eyes", "long hair"], "works": 1000},
            {"trigger": "other", "tags": ["1girl", "blue eyes"], "works": 5000},
        ]
        for seed in range(5):
            output, _, debug = self.node.process_tags(seed=seed, character_sex="Female+Male+Others",
                taglists_must_include="touhou, blue eyes", filter_out_tags="long hair", top_n=2,
                character_count=2, output_mode="trigger")
            self.assertIn("girl, touhou", output)
            self.assertIn("boy, touhou", output)
            self.assertNotIn("robot", output)
            self.assertNotIn("excluded", output)
            self.assertIn("Matching character pool size: 3", debug)
            self.assertIn("Draw pool size: 2", debug)

    def test_multiple_character_output_modes_formats_and_faces(self):
        self.source.return_value = [
            {"trigger": "alice_margatroid, touhou", "tags": ["1girl", "blue_eyes", "^_^", "o_o"]},
            {"trigger": "other_girl, touhou", "tags": ["1girl", "red eyes"]},
        ]
        kwargs = dict(seed=42, character_count=2)
        full = self.node.process_tags(**kwargs)
        sd = self.node.process_tags(**kwargs, tag_form="SD")
        trigger = self.node.process_tags(**kwargs, output_mode="trigger")
        self.assertEqual(full[0], "alice margatroid, touhou, 1girl, blue eyes, ^_^, o_o, other girl, touhou, 1girl, red eyes")
        self.assertEqual(sd[0], "alice_margatroid, touhou, 1girl, blue_eyes, ^_^, o_o, other_girl, touhou, 1girl, red_eyes")
        self.assertEqual(trigger[0], "alice margatroid, touhou, other girl, touhou")
        self.assertEqual(full[2], sd[2])
        self.assertEqual(trigger[2], full[2].replace("Output mode: trigger+tags", "Output mode: trigger"))

    def test_explicit_one_matches_the_default_for_original_seed_results(self):
        for sex in ("Female", "Male", "Others", "Female+Male+Others"):
            for seed in range(10):
                self.assertEqual(self.node.process_tags(seed=seed, character_sex=sex),
                                 self.node.process_tags(seed=seed, character_sex=sex, character_count=1))

    def test_insufficient_filtered_or_top_n_pool_does_not_repeat_or_silently_reduce_count(self):
        for kwargs in (dict(taglists_must_include="touhou, blue eyes"), dict(top_n=1)):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "Draw pool size is 1"):
                self.node.process_tags(character_count=2, **kwargs)
        with self.assertRaisesRegex(ValueError, "Reduce character_count"):
            self.node.process_tags(character_count=5)

    def test_invalid_character_counts_are_rejected(self):
        for value in (0, -1, 1.5, "2", True):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "positive integer"):
                self.node.process_tags(character_count=value)

    def test_character_count_can_exceed_six_and_draw_the_whole_pool(self):
        self.source.return_value = [{"trigger": f"character {index}", "tags": ["1girl"]} for index in range(10)]
        output, unfiltered, debug = self.node.process_tags(character_count=10, output_mode="trigger")
        self.assertEqual(set(output.split(", ")), {f"character {index}" for index in range(10)})
        self.assertEqual(len(output.split(", ")), 10)
        self.assertEqual(output, unfiltered)
        self.assertIn("Character count: 10", debug)


if __name__ == "__main__":
    unittest.main()
