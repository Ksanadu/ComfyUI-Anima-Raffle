import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { registerPreviewHistoryControls } from "./preview_history_controls.js";

registerPreviewHistoryControls(app, api);
