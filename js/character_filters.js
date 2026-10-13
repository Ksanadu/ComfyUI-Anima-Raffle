export const CHARACTER_SEX_OPTIONS = new Set(["female", "male", "others"]);

export function getCharacterSexCategory(item) {
    const tags = Array.isArray(item?.tags) ? item.tags : [item?.tags || ""];
    const parts = [item?.trigger || item?.tag || "", ...tags]
        .flatMap((value) => String(value || "").split(","))
        .map((part) => part.trim().toLowerCase());
    const tagSet = new Set(parts);
    const female = tagSet.has("1girl");
    const male = tagSet.has("1boy");
    if (female && !male) return "female";
    if (male && !female) return "male";
    return "others";
}
