# Data Source and Attribution

This project includes an optional autocomplete dataset and reference materials derived from publicly available style and artist listings from the [Anima Style Explorer](https://thetacursed.github.io/Anima-Style-Explorer).

It can also index artists and characters from [Animadex](https://animadex.net) when the user enables the Animadex index option. Animadex API calls are rate limited locally to avoid hammering the service.

## Bundled offline character text

On 2026-10-17, the character text index was refreshed using the site's official offline CSV export, catalogue version `1780120177`. The export contains 36,492 unique character records, including triggers, core tags, copyrights and post counts. Existing display names and preview references are retained where available; the 15,879 existing artist records are preserved. New records with no supplied description tags remain without inferred tags.

The combined local index is `data/animadex_index.json`; provenance and source CSV checksums are recorded in `data/character_data_source.json`. Browsing and drawing character text use this local file and make no remote requests. No thumbnails or full-resolution images were downloaded in this refresh. Personal export credentials are not included.

The official offline export procedure is documented at [Animadex: importing the public catalogue](https://github.com/zetaneko/AnimaDex/blob/main/docs/import-from-site.md). Credit for the catalogue organization and character metadata remains with Animadex and the original data contributors.

All credit for the original organization, naming, and categorization of styles belongs to its respective creator, **ThetaCursed**.
Preview images for the legacy Anima Style Explorer dataset are loaded from the public [ThetaCursed/Anima-Assets](https://github.com/ThetaCursed/Anima-Assets) image repository.

### Important Notes:
- This repository does not redistribute the original website.
- The dataset used by this node is provided solely for offline autocomplete and style discovery functionality inside the ComfyUI environment.
- This project is a community-driven tool and is not affiliated with the original website maintainers.
- If the original author requests removal or modification of the data pointers, they will be promptly updated.
