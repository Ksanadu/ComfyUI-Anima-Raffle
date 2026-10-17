import math
import random

from . import artist_data
from .raffle import Raffle, format_anima_tag


SORT_METHODS = ("Popularity", "Uniqueness", "A–Z", "Shuffle")
SORT_ORDERS = ("Ascending", "Descending")


def _sort_metric(item, field):
    if field == "uniqueness_score" and "score" in item and item["score"] is None:
        return None
    try:
        value = float(item.get(field))
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _artist_pool(sort_by="A–Z", sort_order="Ascending", shuffle_seed=0):
    artists = {}
    for item in artist_data.load():
        if str(item.get("source_kind") or "").strip().lower() == "character":
            continue
        name = item.get("trigger") or item.get("tag") or ""
        name = "_".join(name.strip().lstrip("@").strip().split())
        if not name:
            continue
        key = name.replace("\\(", "(").replace("\\)", ")").casefold()
        artists.setdefault(key, (name, item))

    keys = sorted(artists)
    if sort_by in ("Popularity", "Uniqueness"):
        field = "works" if sort_by == "Popularity" else "uniqueness_score"
        direction = 1 if sort_order == "Ascending" else -1

        def rank(key):
            value = _sort_metric(artists[key][1], field)
            return (value is None, direction * value if value is not None else 0, key)

        keys.sort(key=rank)
    else:
        if sort_by == "Shuffle":
            random.Random(shuffle_seed).shuffle(keys)
        if sort_order == "Descending":
            keys.reverse()
    return [artists[key][0] for key in keys]


class RaffleArtist(Raffle):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "control_after_generate": True,
                    "tooltip": "Random seed, or sequential batch number. In Sequential mode, set control_after_generate to increment to draw the next batch each run.",
                }),
                "mode": (["Random", "Sequential"], {"default": "Random"}),
                "artist_count": ("INT", {"default": 1, "min": 1, "max": 6}),
                "tag_form": (["Anima", "SD"], {
                    "default": "Anima",
                    "tooltip": "Anima adds @ and uses spaces. SD omits @ and uses underscores.",
                }),
                "sort_by": (list(SORT_METHODS), {
                    "default": "A–Z",
                    "tooltip": "Sequential mode only: sort by work count, uniqueness score, name, or a fixed shuffled order.",
                }),
                "sort_order": (list(SORT_ORDERS), {
                    "default": "Ascending",
                    "tooltip": "Sequential mode only. Ascending: low to high / A–Z / forward shuffle. Descending: high to low / Z–A / reverse shuffle. Missing metrics stay last.",
                }),
                "shuffle_seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "control_after_generate": False,
                    "tooltip": "Fixes the shuffled order in Sequential + Shuffle mode. Keep this unchanged and increment seed to traverse consecutive batches.",
                }),
            },
        }

    OUTPUT_TOOLTIPS = (
        "The selected artist tags, formatted for Anima or SD",
        "The same artist tags; this node does not filter the selected output",
        "Local artist pool size, selection mode, sorting, seed and selected artists",
    )

    def process_tags(self, seed=0, mode="Random", artist_count=1, tag_form="Anima",
                     sort_by="A–Z", sort_order="Ascending", shuffle_seed=0):
        if mode not in ("Random", "Sequential"):
            raise ValueError(f"Unknown artist selection mode: {mode}")
        if tag_form not in ("Anima", "SD"):
            raise ValueError(f"Unknown tag form: {tag_form}")
        if not isinstance(artist_count, int) or not 1 <= artist_count <= 6:
            raise ValueError("Artist count must be an integer from 1 to 6.")
        if sort_by not in SORT_METHODS:
            raise ValueError(f"Unknown artist sort method: {sort_by}")
        if sort_order not in SORT_ORDERS:
            raise ValueError(f"Unknown artist sort order: {sort_order}")

        artists = _artist_pool(sort_by, sort_order, shuffle_seed) if mode == "Sequential" else _artist_pool()
        if not artists:
            raise ValueError("The local artist index is empty. Update it from Anima Style Explorer's Styles tab.")
        if artist_count > len(artists):
            raise ValueError(f"Only {len(artists)} unique artists are available; reduce artist_count.")

        if mode == "Random":
            selected = random.Random(seed).sample(artists, artist_count)
        else:
            start = (seed * artist_count) % len(artists)
            selected = [artists[(start + index) % len(artists)] for index in range(artist_count)]

        tags = ["@" + format_anima_tag(name) for name in selected] if tag_form == "Anima" else selected
        output = ", ".join(tags)
        ordering = ""
        if mode == "Sequential":
            ordering = f"Sort by: {sort_by}\nSort order: {sort_order}\n"
            if sort_by == "Shuffle":
                ordering += f"Shuffle seed: {shuffle_seed}\n"
        debug = (
            "Source: Anima Style Explorer / local artists (Theta + Animadex)\n"
            f"Artist pool size: {len(artists)}\n"
            f"Mode: {mode}\n"
            f"{ordering}"
            f"Seed: {seed}\n"
            f"Artist count: {artist_count}\n"
            f"Selected artists: {', '.join(selected)}"
        )
        return output, output, debug


NODE_CLASS_MAPPINGS = {"RaffleArtist": RaffleArtist}
NODE_DISPLAY_NAME_MAPPINGS = {"RaffleArtist": "Raffle Artist"}
