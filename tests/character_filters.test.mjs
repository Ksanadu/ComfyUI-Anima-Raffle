import assert from "node:assert/strict";
import { test } from "node:test";
import { getCharacterSexCategory } from "../js/character_filters.js";

test("classifies the complete trigger and tags, independent of insertion mode", () => {
    assert.equal(getCharacterSexCategory({ trigger: "character, series", tags: ["1girl", "blue hair"] }), "female");
    assert.equal(getCharacterSexCategory({ trigger: "character, 1boy", tags: ["short hair"] }), "male");
    assert.equal(getCharacterSexCategory({ trigger: "character", tags: "1boy, short hair" }), "male");
    assert.equal(getCharacterSexCategory({ tag: "character, 1girl", tags: [] }), "female");
});

test("keeps mixed and unclassified characters in Others", () => {
    assert.equal(getCharacterSexCategory({ trigger: "1girl", tags: ["1boy"] }), "others");
    assert.equal(getCharacterSexCategory({ tags: ["2girls", "1girl_focus"] }), "others");
    assert.equal(getCharacterSexCategory({ tags: [] }), "others");
});

test("matches whole tags and tolerates case and whitespace", () => {
    assert.equal(getCharacterSexCategory({ tags: [" 1GIRL "] }), "female");
    assert.equal(getCharacterSexCategory({ tags: ["1boy, smile"] }), "male");
    assert.equal(getCharacterSexCategory({ trigger: "some_1girl_character" }), "others");
});
