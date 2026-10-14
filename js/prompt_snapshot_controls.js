const SNAPSHOT_KEY = "anima_prompt_snapshot";
const REQUEST_KEY = "anima_prompt_snapshot_request";

export function registerPromptSnapshot(app, ComfyWidgets, api) {
    const completedSnapshots = new Map();
    function rememberSnapshot(message) {
        const requestId = message?.snapshot_request?.[0];
        const text = message?.saved_text?.[0];
        if (typeof requestId !== "string" || !requestId || typeof text !== "string") return;
        completedSnapshots.delete(requestId);
        completedSnapshots.set(requestId, text);
        if (completedSnapshots.size > 256) completedSnapshots.delete(completedSnapshots.keys().next().value);
    }
    app.registerExtension({
        name: "AnimaRaffle.PromptSnapshot",
        setup() {
            // Executed events arrive even when another workflow is active.
            // Keep them by request UUID, never by a possibly reused node ID.
            api?.addEventListener("executed", ({ detail }) => rememberSnapshot(detail?.output));
        },
        beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData.name !== "PromptSnapshot") return;
            const originalCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = originalCreated?.apply(this, arguments);
                const node = this;
                node.properties ??= {};
                const pendingRequests = new Set();
                let restored = false;
                const widget = ComfyWidgets.STRING(node, "Saved prompt", ["STRING", {
                    multiline: true, default: "",
                }], app).widget;
                widget.serialize = false;
                widget.options.serialize = false;
                const inputEl = widget.element ?? widget.inputEl;
                inputEl.readOnly = true;
                inputEl.placeholder = "The received prompt will be saved in the image workflow.";
                widget.beforeQueued = () => {
                    const requestId = crypto.randomUUID();
                    node.properties[REQUEST_KEY] = requestId;
                    pendingRequests.add(requestId);
                };

                function showSavedPrompt() {
                    const text = node.properties[SNAPSHOT_KEY];
                    widget.value = typeof text === "string" ? text : "";
                    node.setDirtyCanvas?.(true, true);
                }

                const originalConfigure = node.onConfigure;
                node.onConfigure = function () {
                    const value = originalConfigure?.apply(this, arguments);
                    restored = true;
                    pendingRequests.clear();
                    const requestId = node.properties[REQUEST_KEY];
                    if (completedSnapshots.has(requestId)) {
                        node.properties[SNAPSHOT_KEY] = completedSnapshots.get(requestId);
                    }
                    showSavedPrompt();
                    return value;
                };
                const originalExecuted = node.onExecuted;
                node.onExecuted = function (message) {
                    const text = message?.saved_text?.[0];
                    if (typeof text !== "string") return;
                    const requestId = message.snapshot_request?.[0];
                    // A late event from another queued workflow must not overwrite
                    // the snapshot restored by opening an older image.
                    const expected = requestId && (pendingRequests.has(requestId)
                        || requestId === node.properties[REQUEST_KEY]);
                    if (!expected && (restored || requestId)) return;
                    pendingRequests.delete(requestId);
                    rememberSnapshot(message);
                    const value = originalExecuted?.apply(this, arguments);
                    node.properties[SNAPSHOT_KEY] = text;
                    showSavedPrompt();
                    return value;
                };
                showSavedPrompt();
                return result;
            };
        },
    });
}
