import assert from "node:assert/strict";
import { test } from "node:test";
import { formatAnimaTag, splitPromptTagList } from "../js/tag_format.js";

test("preserves symbolic tags, letter eyes and repeated underscores", () => {
    for (const face of ["^_^", "o_o", ">_<", "@_@", "._.", "T_T", "0_0", "<|>_<|>", "mg_mg", "=__=", ">_o"]) {
        assert.equal(formatAnimaTag(face), face);
    }
});

test("formats ordinary tags including short words and artist initials", () => {
    for (const [tag, expected] of [["best_quality", "best quality"], ["m_k", "m k"],
        ["au_ra", "au ra"], ["k_on!", "k on!"], ["a_cup", "a cup"], ["cz_75", "cz 75"], ["青_目", "青 目"]]) {
        assert.equal(formatAnimaTag(tag), expected);
    }
});

test("character insertion and copy retain faces and decode ordinary tags", () => {
    assert.deepEqual(splitPromptTagList(["character_\\(series\\)", "1girl, best_quality", "^_^", "o_o", "@_@"]),
        ["character (series)", "1girl", "best quality", "^_^", "o_o", "@_@"]);
    assert.deepEqual(splitPromptTagList("@some_artist, o_o"), ["some artist", "o_o"]);
});
