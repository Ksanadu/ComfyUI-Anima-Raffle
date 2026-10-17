import random

from . import artist_data
from .raffle import Raffle, format_anima_tag


def _artist_pool():
    artists = {}
    for item in artist_data.load():
        if str(item.get("source_kind") or "").strip().lower() == "character":
            continue
        name = item.get("trigger") or item.get("tag") or ""
        name = "_".join(name.strip().lstrip("@").strip().split())
        if not name:
            continue
        key = name.replace("\\(", "(").replace("\\)", ")").casefold()
        artists.setdefault(key, name)
    return [artists[key] for key in sorted(artists)]


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
            },
        }

    OUTPUT_TOOLTIPS = (
        "The selected artist tags, formatted for Anima or SD",
        "The same artist tags; this node does not filter the selected output",
        "Local artist pool size, selection mode, seed and selected artists",
    )

    def process_tags(self, seed=0, mode="Random", artist_count=1, tag_form="Anima"):
        if mode not in ("Random", "Sequential"):
            raise ValueError(f"Unknown artist selection mode: {mode}")
        if tag_form not in ("Anima", "SD"):
            raise ValueError(f"Unknown tag form: {tag_form}")
        if not isinstance(artist_count, int) or not 1 <= artist_count <= 6:
            raise ValueError("Artist count must be an integer from 1 to 6.")

        artists = _artist_pool()
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
        debug = (
            "Source: Anima Style Explorer / local artists (Theta + Animadex)\n"
            f"Artist pool size: {len(artists)}\n"
            f"Mode: {mode}\n"
            f"Seed: {seed}\n"
            f"Artist count: {artist_count}\n"
            f"Selected artists: {', '.join(selected)}"
        )
        return output, output, debug


NODE_CLASS_MAPPINGS = {"RaffleArtist": RaffleArtist}
NODE_DISPLAY_NAME_MAPPINGS = {"RaffleArtist": "Raffle Artist"}
