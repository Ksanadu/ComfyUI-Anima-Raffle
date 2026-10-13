import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("raffle_under_test", ROOT / "raffle.py")
raffle = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"folder_paths": types.ModuleType("folder_paths")}):
    spec.loader.exec_module(raffle)


class RaffleFormatTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        lists = root / "lists"
        lists.mkdir()
        (lists / "categorized_tags.txt").write_text(
            "[character_count] 1girl\n[character_count] 1boy\n"
            "[artstyle_technique] best_quality\n"
            "[sfw_clothed_anatomy] blue_hair\n"
            "[expressions_and_mental_state] smile\n"
            "[artist] example_artist\n", encoding="utf-8",
        )
        for rating in ("general", "questionable", "sensitive", "explicit"):
            (lists / f"taglists-{rating}.txt").write_text(
                "1girl,best_quality,blue_hair,smile,example_artist\n"
                "1boy,best_quality,smile\n", encoding="utf-8",
            )
        file_patch = patch.object(raffle, "__file__", str(root / "raffle.py"))
        file_patch.start()
        self.addCleanup(file_patch.stop)
        self.kwargs = dict(
            exclude_taglists_containing="1boy", taglists_must_include="1girl",
            seed=17, use_general=True, use_questionable=False,
            use_sensitive=False, use_explicit=False, exclude_tag_categories="artist",
        )

    def test_sd_keeps_original_tags_and_default(self):
        node = raffle.Raffle()
        result = node.process_tags(**self.kwargs, tag_form="SD")
        self.assertEqual(result, node.process_tags(**self.kwargs))
        self.assertEqual(result[0], "1girl, best_quality, blue_hair, smile")
        self.assertEqual(result[1], "1girl, best_quality, blue_hair, smile, example_artist")

    def test_anima_formats_both_outputs_after_filtering(self):
        node = raffle.Raffle()
        kwargs = dict(self.kwargs, negative_prompt="blue hair", filter_out_tags="smile")
        sd = node.process_tags(**kwargs, tag_form="SD")
        anima = node.process_tags(**kwargs, tag_form="Anima")
        self.assertEqual(anima[0], "1girl, best quality")
        self.assertEqual(anima[1], "1girl, best quality, blue hair, smile, example artist")
        self.assertEqual(anima[2], sd[2])

    def test_all_rating_pools_support_both_forms(self):
        for rating in ("general", "questionable", "sensitive", "explicit"):
            kwargs = dict(self.kwargs, **{
                f"use_{name}": name == rating
                for name in ("general", "questionable", "sensitive", "explicit")
            })
            for seed in (0, 1, 99):
                kwargs["seed"] = seed
                with self.subTest(rating=rating, seed=seed):
                    node = raffle.Raffle()
                    sd = node.process_tags(**kwargs, tag_form="SD")
                    anima = node.process_tags(**kwargs, tag_form="Anima")
                    self.assertEqual(anima[:2], tuple(value.replace("_", " ") for value in sd[:2]))
                    self.assertEqual(anima[2], sd[2])

    def test_empty_pool_still_reports_selection_error(self):
        with self.assertRaisesRegex(ValueError, "No tags available"):
            raffle.Raffle().process_tags(**dict(self.kwargs, taglists_must_include="missing_tag"))

    def test_emoticons_survive_both_outputs_with_word_tags(self):
        faces = ["^_^", "o_o", ">_<", "@_@", "._.", "T_T", "0_0", "<|>_<|>", "mg_mg", "=__=", ">_o"]
        words = ["a_cup", "m_k", "au_ra", "k_on!", "cz_75", "青_目"]
        lists = Path(raffle.__file__).parent / "lists"
        with (lists / "categorized_tags.txt").open("a", encoding="utf-8") as file:
            for tag in faces + words:
                file.write(f"[expressions_and_mental_state] {tag}\n")
        (lists / "taglists-general.txt").write_text(
            ",".join(["1girl", "best_quality"] + faces + words), encoding="utf-8",
        )
        node = raffle.Raffle()
        anima = node.process_tags(**self.kwargs, tag_form="Anima")
        expected = ", ".join(["1girl", "best quality"] + faces + ["a cup", "m k", "au ra", "k on!", "cz 75", "青 目"])
        self.assertEqual(anima[:2], (expected, expected))
        sd = node.process_tags(**self.kwargs, tag_form="SD")
        self.assertIn("best_quality", sd[0])
        self.assertEqual(anima[2], sd[2])

    def test_emoticons_remain_filterable_before_formatting(self):
        lists = Path(raffle.__file__).parent / "lists"
        with (lists / "categorized_tags.txt").open("a", encoding="utf-8") as file:
            file.write("[expressions_and_mental_state] ^_^\n[expressions_and_mental_state] o_o\n")
        (lists / "taglists-general.txt").write_text("1girl,best_quality,^_^,o_o", encoding="utf-8")
        result = raffle.Raffle().process_tags(**self.kwargs, tag_form="Anima",
                                             negative_prompt="o_o", filter_out_tags="^_^")
        self.assertEqual(result[0], "1girl, best quality")
        self.assertEqual(result[1], "1girl, best quality, ^_^, o_o")


if __name__ == "__main__":
    unittest.main()
