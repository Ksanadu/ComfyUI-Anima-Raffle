import assert from "node:assert/strict";
import { test } from "node:test";
import { registerPreviewHistoryControls } from "../js/preview_history_controls.js";

function fixture(fetchApi) {
    class PreviewNode {
        constructor(id = 1) {
            this.id = id;
            this.comfyClass = "PreviewHistory";
            this.widgets = [{ name: "history_size", value: 9 }];
            this.imgs = ["old"];
            this.images = [{ filename: "old.png" }];
            this.onNodeCreated();
        }
        addWidget(type, name, value, callback, options) {
            const widget = { type, name, value, callback, options };
            this.widgets.push(widget);
            return widget;
        }
        onNodeCreated() { this.originalCalled = true; }
        setDirtyCanvas() {}
    }
    const messages = [];
    const events = new EventTarget();
    const executed = [];
    const app = {
        graph: { _nodes: [] }, canvas: { setDirty() {} },
        ui: { dialog: { show: message => messages.push(message) } },
        registerExtension(extension) { this.extension = extension; },
    };
    const api = {
        fetchApi,
        addEventListener: (...args) => events.addEventListener(...args),
        dispatchEvent(event) {
            if (event.type === "executed") executed.push(event.detail);
            return events.dispatchEvent(event);
        },
    };
    registerPreviewHistoryControls(app, api);
    app.extension.setup();
    app.extension.beforeRegisterNodeDef(PreviewNode, { name: "PreviewHistory" });
    const node = new PreviewNode();
    app.graph._nodes.push(node);
    return { app, api, node, PreviewNode, messages, executed, button: node.widgets[1] };
}

test("button preserves original lifecycle and is excluded from saved widget slots", () => {
    const { app, node, button } = fixture();
    assert.equal(node.originalCalled, true);
    assert.equal(button.name, "Clear History");
    assert.equal(button.serialize, false);
    assert.equal(button.options.serialize, false);
    assert.deepEqual(node.widgets.filter(widget => widget.serialize !== false).map(widget => widget.value), [9]);
    class OtherNode {}
    app.extension.beforeRegisterNodeDef(OtherNode, { name: "SaveImage" });
    assert.equal(OtherNode.prototype.onNodeCreated, undefined);
});

test("one click uses local token, clears all history previews and preserves other nodes", async () => {
    const calls = [];
    const data = fixture(async (url, options) => {
        calls.push([url, options]);
        return { ok: true, json: async () => url.endsWith("fullet_local_token") ? { localToken: "token" } : { success: true } };
    });
    const other = { id: 2, comfyClass: "SaveImage", imgs: ["saved"], images: ["saved"] };
    const second = new data.PreviewNode(3);
    const nested = new data.PreviewNode(5);
    data.app.graph._nodes.push(other, second, { id: 4, subgraph: { nodes: [nested] } });
    await data.button.callback();
    assert.deepEqual(calls, [
        ["/anima/fullet_local_token", undefined],
        ["/anima/preview_history/clear", { method: "POST", headers: { "x-anima-local-token": "token" } }],
    ]);
    for (const node of [data.node, second, nested]) {
        assert.equal(node.imgs, null);
        assert.deepEqual(node.images, []);
    }
    assert.deepEqual(other.imgs, ["saved"]);
    assert.deepEqual(data.executed.map(event => event.node), ["1", "3", "4:5"]);
    assert.ok(data.executed.every(event => !event.merge && event.output.images.length === 0));
    assert.equal(data.button.name, "Clear History");
});

test("broadcast clears previews in another connected client without clicking", () => {
    const data = fixture();
    data.api.dispatchEvent(new CustomEvent("raffle.preview_history.cleared"));
    assert.deepEqual(data.node.images, []);
    assert.equal(data.node.imgs, null);
});

test("duplicate clicks issue only one request while clearing", async () => {
    let release;
    const waiting = new Promise(resolve => { release = resolve; });
    let calls = 0;
    const data = fixture(async url => {
        calls++;
        await waiting;
        return { ok: true, json: async () => url.endsWith("fullet_local_token") ? { localToken: "token" } : { success: true } };
    });
    const first = data.button.callback();
    await data.button.callback();
    assert.equal(calls, 1);
    assert.equal(data.button.name, "Clearing...");
    release();
    await first;
    assert.equal(calls, 2);
    assert.equal(data.button.name, "Clear History");
});

test("failure shows the error, preserves previews and allows retry", async () => {
    let succeeds = false;
    const data = fixture(async url => ({
        ok: url.endsWith("fullet_local_token") || succeeds,
        json: async () => url.endsWith("fullet_local_token") ? { localToken: "token" } : { success: succeeds, error: "locked" },
    }));
    const originalError = console.error;
    console.error = () => {};
    try {
        await data.button.callback();
    } finally {
        console.error = originalError;
    }
    assert.deepEqual(data.node.imgs, ["old"]);
    assert.deepEqual(data.messages, ["Clear History failed: locked"]);
    assert.equal(data.button.name, "Clear History");
    succeeds = true;
    await data.button.callback();
    assert.deepEqual(data.node.images, []);
});
