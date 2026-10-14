import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { registerPromptSnapshot } from "./prompt_snapshot_controls.js";

registerPromptSnapshot(app, ComfyWidgets);
