import assert from "node:assert/strict";
import { test } from "node:test";
import { registerPromptSnapshot } from "../js/prompt_snapshot_controls.js";

const SNAPSHOT = "anima_prompt_snapshot";
const REQUEST = "anima_prompt_snapshot_request";

function fixture() {
    class SnapshotNode {
        constructor() {
            this.properties = {};
            this.widgets = [];
            this.onNodeCreated();
        }
        onNodeCreated() { this.createdCalled = true; }
        onConfigure() { this.configureCalled = true; }
        onExecuted() { this.executedCalled = true; }
        setDirtyCanvas() {}
    }
    const app = { registerExtension(extension) { this.extension = extension; } };
    const api = new EventTarget();
    const widgets = {
        STRING(node) {
            const widget = { value: "", options: {}, inputEl: {} };
            node.widgets.push(widget);
            return { widget };
        },
    };
    registerPromptSnapshot(app, widgets, api);
    app.extension.setup();
    app.extension.beforeRegisterNodeDef(SnapshotNode, { name: "PromptSnapshot" });
    const node = new SnapshotNode();
    return { app, api, node, widget: node.widgets[0] };
}

function queue(node, widget) {
    widget.beforeQueued();
    return node.properties[REQUEST];
}

function executed(node, text, request) {
    node.onExecuted({ saved_text: [text], snapshot_request: [request] });
}

test("readonly snapshot preserves lifecycle and adds no serialized input slots", () => {
    const { app, node, widget } = fixture();
    assert.equal(node.createdCalled, true);
    assert.equal(widget.inputEl.readOnly, true);
    assert.equal(widget.serialize, false);
    assert.equal(widget.options.serialize, false);
    class OtherNode {}
    app.extension.beforeRegisterNodeDef(OtherNode, { name: "ShowAny" });
    assert.equal(OtherNode.prototype.onNodeCreated, undefined);
});

test("live execution records exact text as a workflow property", () => {
    const { node, widget } = fixture();
    const request = queue(node, widget);
    const text = "  中文, ^_^, o_o\nsecond line  ";
    executed(node, text, request);
    assert.equal(widget.value, text);
    assert.equal(node.properties[SNAPSHOT], text);
    assert.equal(node.executedCalled, true);
});

test("loading picture A restores A and ignores late results from picture B", () => {
    const { node, widget } = fixture();
    const oldRequest = queue(node, widget);
    executed(node, "picture B", oldRequest);
    node.properties = { [SNAPSHOT]: "picture A", [REQUEST]: "job-a" };
    node.onConfigure();
    assert.equal(node.configureCalled, true);
    assert.equal(widget.value, "picture A");
    executed(node, "picture B", oldRequest);
    executed(node, "stale cached output", "");
    node.onExecuted({ text: ["other node's cached text"] });
    assert.equal(widget.value, "picture A");
    assert.equal(node.properties[SNAPSHOT], "picture A");
});

test("a new execution after loading an image replaces the snapshot normally", () => {
    const { node, widget } = fixture();
    node.properties = { [SNAPSHOT]: "picture A", [REQUEST]: "job-a" };
    node.onConfigure();
    executed(node, "picture C", queue(node, widget));
    assert.equal(widget.value, "picture C");
    assert.equal(node.properties[SNAPSHOT], "picture C");
});

test("multiple queued jobs can display their own results in execution order", () => {
    const { node, widget } = fixture();
    const first = queue(node, widget);
    const second = queue(node, widget);
    assert.notEqual(first, second);
    executed(node, "first", first);
    assert.equal(widget.value, "first");
    executed(node, "second", second);
    assert.equal(widget.value, "second");
});

test("empty saved text is restored and is not replaced by a previous workflow", () => {
    const { node, widget } = fixture();
    executed(node, "old", queue(node, widget));
    node.properties = { [SNAPSHOT]: "", [REQUEST]: "empty-job" };
    node.onConfigure();
    assert.equal(widget.value, "");
    node.properties = {};
    node.onConfigure();
    assert.equal(widget.value, "");
});

test("returning to an inactive workflow restores its completed background prompt", () => {
    const { api, node, widget } = fixture();
    node.properties = { [SNAPSHOT]: "previous picture", [REQUEST]: "background-job" };
    api.dispatchEvent(new CustomEvent("executed", { detail: {
        node: "137", output: { saved_text: ["this picture"], snapshot_request: ["background-job"] },
    } }));
    // ComfyUI did not call this inactive node's onExecuted callback.
    assert.equal(node.executedCalled, undefined);
    node.onConfigure();
    assert.equal(widget.value, "this picture");
    assert.equal(node.properties[SNAPSHOT], "this picture");
});

test("background results with reused node IDs cannot replace an older image's snapshot", () => {
    const { api, node, widget } = fixture();
    api.dispatchEvent(new CustomEvent("executed", { detail: {
        node: "137", output: { saved_text: ["picture B"], snapshot_request: ["job-b"] },
    } }));
    node.properties = { [SNAPSHOT]: "picture A", [REQUEST]: "job-a" };
    node.onConfigure();
    assert.equal(widget.value, "picture A");
    node.properties = { [SNAPSHOT]: "stale B preview", [REQUEST]: "job-b" };
    node.onConfigure();
    assert.equal(widget.value, "picture B");
});

test("unrelated executed output and missing request UUID cannot overwrite saved text", () => {
    const { api, node, widget } = fixture();
    for (const output of [{ text: ["other node"] }, { saved_text: ["no job ID"] }]) {
        api.dispatchEvent(new CustomEvent("executed", { detail: { node: "137", output } }));
    }
    node.properties = { [SNAPSHOT]: "recorded prompt", [REQUEST]: "job-a" };
    node.onConfigure();
    assert.equal(widget.value, "recorded prompt");
});
