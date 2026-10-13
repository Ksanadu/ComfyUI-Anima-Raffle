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
        })
        self.assertEqual(schema["required"]["taglists_must_include"][1]["default"], "")
        self.assertEqual(schema["required"]["filter_out_tags"][1]["default"], "")
        self.assertEqual(schema["required"]["character_sex"][1]["default"], "Female")
        self.assertEqual(schema["required"]["tag_form"][1]["default"], "Anima")
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

    def test_empty_source_and_conflicting_filters_do_not_fall_back(self):
        with self.assertRaisesRegex(ValueError, "No matching"):
            self.node.process_tags(taglists_must_include="touhou", filter_out_tags="touhou")
        self.source.return_value = []
        with self.assertRaisesRegex(ValueError, "character index is empty"):
            self.node.process_tags()


if __name__ == "__main__":
    unittest.main()
