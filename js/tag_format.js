const EMOTICON_TAG_RE = /^(?:[0-9oOuUxXtTvVqQ]|[^\p{L}\p{N}_\s]+)_+(?:[0-9oOuUxXtTvVqQ]|[^\p{L}\p{N}_\s]+)$/u;

export function isEmoticonTag(tag) {
    const value = String(tag || "").trim();
    return EMOTICON_TAG_RE.test(value) || value.toLowerCase() === "mg_mg";
}

export function formatAnimaTag(tag) {
    const value = String(tag || "");
    return isEmoticonTag(value) ? value : value.replace(/_/g, " ");
}

export function splitPromptTagList(value = []) {
    const raw = Array.isArray(value) ? value : [value];
    return raw
        .flatMap((item) => String(item || "").split(","))
        .map((part) => {
            const tag = part.trim().replace(/\\([()])/g, "$1");
            const clean = isEmoticonTag(tag) ? tag : tag.replace(/^@+/, "");
            return formatAnimaTag(clean).replace(/\s+/g, " ").trim();
        })
        .filter(Boolean);
}
