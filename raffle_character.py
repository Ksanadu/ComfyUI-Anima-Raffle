import random

from . import artist_data
from .raffle import Raffle, format_anima_tag


def _tag_key(tag):
    return tag.replace("\\(", "(").replace("\\)", ")").casefold()


def _character_sex(tags):
    female = "1girl" in tags
    male = "1boy" in tags
    if female and not male:
        return "female"
    if male and not female:
        return "male"
    return "others"


class RaffleCharacter(Raffle):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "taglists_must_include": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Only draw characters containing ALL these tags in trigger + tags. Use commas or newlines, e.g. touhou, blue eyes. Spaces and underscores both work.",
                }),
                "filter_out_tags": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Exclude characters containing ANY of these tags. This filters the character pool, not the selected character's output tags.",
                }),
                "tag_form": (["Anima", "SD"], {"default": "Anima"}),
                "character_sex": (["Female", "Male", "Others"], {"default": "Female"}),
            },
        }

    OUTPUT_TOOLTIPS = (
        "The selected character's complete trigger + tags in the chosen tag format",
        "The same complete trigger + tags; exclusions filter characters before drawing",
        "Data source, matching pool size, seed, filters and selected character",
    )

    def process_tags(self, taglists_must_include="", filter_out_tags="", seed=0,
                     tag_form="Anima", character_sex="Female"):
        sex = character_sex.strip().lower()
        if sex not in ("female", "male", "others"):
            raise ValueError(f"Unknown Character Sex: {character_sex}")
        if tag_form not in ("Anima", "SD"):
            raise ValueError(f"Unknown tag form: {tag_form}")

        required = {_tag_key(tag) for tag in self.normalize_tags(taglists_must_include)}
        excluded = {_tag_key(tag) for tag in self.normalize_tags(filter_out_tags)}
        characters = artist_data.load_animadex("character")
        candidates = []
        for character in characters:
            trigger = character.get("trigger") or character.get("tag") or ""
            if not trigger:
                continue
            descriptions = character.get("tags") or []
            if isinstance(descriptions, str):
                descriptions = [descriptions]
            tags = self.normalize_tags(", ".join([trigger, *descriptions]))
            keys = {_tag_key(tag) for tag in tags}
            if _character_sex(keys) != sex:
                continue
            if not required.issubset(keys) or not excluded.isdisjoint(keys):
                continue
            candidates.append((character, tags))

        if not candidates:
            raise ValueError(
                f"No matching {character_sex} characters. Relax the tag filters or change Character Sex; "
                "if the character index is empty, update it from Anima Style Explorer's Characters tab."
            )

        character, tags = random.Random(seed).choice(candidates)
        if tag_form == "Anima":
            tags = [format_anima_tag(tag) for tag in tags]
        output = ", ".join(tags)
        debug = (
            "Source: Anima Style Explorer / Animadex characters\n"
            f"Character index size: {len(characters)}\n"
            f"Matching character pool size: {len(candidates)}\n"
            f"Character Sex: {character_sex}\n"
            f"Seed: {seed}\n"
            f"Selected character: {character.get('trigger') or character.get('tag')}\n"
            f"Must include: {taglists_must_include or '(none)'}\n"
            f"Exclude: {filter_out_tags or '(none)'}"
        )
        return output, output, debug


NODE_CLASS_MAPPINGS = {"RaffleCharacter": RaffleCharacter}
NODE_DISPLAY_NAME_MAPPINGS = {"RaffleCharacter": "Raffle Character"}
