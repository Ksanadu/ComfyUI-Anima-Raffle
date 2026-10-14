const CLEARED_EVENT = "raffle.preview_history.cleared";

function clearPreviews(app, api) {
    function visit(graph, parentPath = "", ancestors = new Set()) {
        if (!graph || ancestors.has(graph)) return;
        const nextAncestors = new Set(ancestors).add(graph);
        for (const node of graph.nodes ?? graph._nodes ?? []) {
            const executionId = parentPath ? `${parentPath}:${node.id}` : String(node.id);
            if ((node.comfyClass ?? node.type) === "PreviewHistory") {
                // The normal executed event updates both legacy and Vue output stores.
                api.dispatchEvent(new CustomEvent("executed", {
                    detail: { node: executionId, output: { images: [] }, merge: false },
                }));
                node.imgs = null;
                node.images = [];
                node.imageIndex = null;
                node.overIndex = null;
                node.setDirtyCanvas?.(true, true);
            }
            if (node.subgraph) visit(node.subgraph, executionId, nextAncestors);
        }
    }
    visit(app.rootGraph ?? app.graph);
    app.canvas?.setDirty(true, true);
}

export function registerPreviewHistoryControls(app, api) {
    app.registerExtension({
        name: "AnimaRaffle.PreviewHistory",
        setup() {
            api.addEventListener(CLEARED_EVENT, () => clearPreviews(app, api));
        },
        beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData.name !== "PreviewHistory") return;
            const original = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = original?.apply(this, arguments);
                const node = this;
                let busy = false;
                const button = node.addWidget("button", "Clear History", null, async () => {
                    if (busy) return;
                    busy = true;
                    button.name = "Clearing...";
                    node.setDirtyCanvas?.(true, true);
                    try {
                        const tokenResponse = await api.fetchApi("/anima/fullet_local_token");
                        if (!tokenResponse.ok) throw new Error("Could not obtain local request token.");
                        const { localToken } = await tokenResponse.json();
                        if (!localToken) throw new Error("Missing local request token.");
                        const response = await api.fetchApi("/anima/preview_history/clear", {
                            method: "POST",
                            headers: { "x-anima-local-token": localToken },
                        });
                        const data = await response.json();
                        if (!response.ok || !data.success) {
                            throw new Error(data.error || "Could not clear history.");
                        }
                        clearPreviews(app, api);
                    } catch (error) {
                        console.error("[PreviewHistory] Clear failed:", error);
                        app.ui.dialog.show(`Clear History failed: ${error.message}`);
                    } finally {
                        busy = false;
                        button.name = "Clear History";
                        node.setDirtyCanvas?.(true, true);
                    }
                }, { serialize: false });
                button.serialize = false;
                button.options.tooltip = "Clear shared Preview History images and temporary previews.";
                return result;
            };
        },
    });
}
