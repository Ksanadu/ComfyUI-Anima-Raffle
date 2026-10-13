import { Data } from "./data.js";
import { thumbUrl } from "./utils.js";
import { splitPromptTagList } from "./tag_format.js";

export const AC = (() => {
    let el, ta, atIdx = -1, _debounceTimer = null;

    function init() {
        if (document.getElementById("anima-ac")) return;
        el = document.createElement("div");
        el.id = "anima-ac";
        el.className = "hidden";
        document.body.appendChild(el);
        el.addEventListener("mousedown", e => e.preventDefault());
    }

    function attach(textarea) {
        init();
        if (textarea.dataset.animaAcAttached) return;
        textarea.dataset.animaAcAttached = "true";
        textarea.addEventListener("input", () => {
            clearTimeout(_debounceTimer);
            _debounceTimer = setTimeout(() => _onInput(textarea), 150);
        });
        textarea.addEventListener("keydown", e => _onKey(e));
        textarea.addEventListener("blur", () => setTimeout(hide, 160));
    }

    async function _onInput(textarea) {
        ta = textarea;
        const before = textarea.value.slice(0, textarea.selectionStart);
        const m = before.match(/@([^,\n]*)$/);
        if (!m) { hide(); return; }

        atIdx = before.lastIndexOf("@");
        const results = await Data.search(m[1].trim());
        if (!results.length) { hide(); return; }

        const r = textarea.getBoundingClientRect();
        el.style.left = `${r.left + window.scrollX}px`;
        el.style.top = `${r.bottom + window.scrollY + 3}px`;
        el.style.width = `${Math.max(240, r.width * .65)}px`;
        el.innerHTML = "";
        el.classList.remove("hidden");

        results.slice(0, 15).forEach((a, i) => {
            const row = document.createElement("div");
            row.className = "anima-ac-row" + (i === 0 ? " on" : "");
            row.dataset.tag = a.tag;
            const kind = String(a?.source_kind || "").toLowerCase();
            const kindLabel = kind === "character" ? "CHARACTER" : kind === "artist" ? "STYLE" : "";
            const displayTag = kind === "character"
                ? String(a?.trigger || a?.tag || "").replace(/^@+/, "")
                : `@${a.tag}`;
            row._artist = a;
            row.innerHTML = `
                <img class="anima-ac-thumb" src="${thumbUrl(a)}" alt="" onerror="this.style.display='none'"/>
                <span class="anima-ac-tag">${displayTag}</span>
                ${kindLabel ? `<span class="anima-ac-kind anima-ac-kind-${kind}">${kindLabel}</span>` : ""}
                ${a.works ? `<span class="anima-ac-works">${a.works.toLocaleString()}</span>` : ""}
            `;
            row.addEventListener("mousedown", () => _pick(a));
            el.appendChild(row);
        });
    }

    function _onKey(e) {
        if (!el || el.classList.contains("hidden")) return;
        const rows = [...el.querySelectorAll(".anima-ac-row")];
        const cur = el.querySelector(".anima-ac-row.on");
        const idx = rows.indexOf(cur);
        if (e.key === "ArrowDown") { e.preventDefault(); cur?.classList.remove("on"); rows[(idx + 1) % rows.length]?.classList.add("on"); }
        else if (e.key === "ArrowUp") { e.preventDefault(); cur?.classList.remove("on"); rows[(idx - 1 + rows.length) % rows.length]?.classList.add("on"); }
        else if (e.key === "Enter" || e.key === "Tab") { const on = el.querySelector(".anima-ac-row.on"); if (on) { e.preventDefault(); _pick(on._artist || { tag: on.dataset.tag }); } }
        else if (e.key === "Escape") { hide(); }
    }

    function _pick(artist) {
        if (!ta) return;
        const val = ta.value;
        const cursor = ta.selectionStart;
        const before = val.slice(0, atIdx);
        const after = val.slice(cursor).replace(/^,?\s*/, "");
        const kind = String(artist?.source_kind || "").toLowerCase();
        const spaceTag = splitPromptTagList(kind === "character" ? (artist.trigger || artist.tag) : artist.tag).join(", ");
        const insert = kind === "character" ? spaceTag : `@${spaceTag}`;
        ta.value = `${before}${insert}, ${after}`.trimEnd();
        const pos = before.length + insert.length;
        ta.setSelectionRange(pos, pos);
        ta.dispatchEvent(new Event("input", { bubbles: true }));
        ta.dispatchEvent(new Event("change", { bubbles: true }));
        hide();
    }

    function hide() { el?.classList.add("hidden"); }
    return { attach };
})();
