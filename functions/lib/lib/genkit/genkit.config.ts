"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const vertexai_1 = require("@genkit-ai/vertexai");
const core_1 = require("@genkit-ai/core");
const firebase_1 = require("@genkit-ai/firebase");
exports.default = (0, core_1.configureGenkit)({
    plugins: [
        (0, firebase_1.firebase)(),
        (0, vertexai_1.vertexAI)({ location: "us-central1" }),
    ],
    logLevel: "debug",
    enableTracingAndMetrics: true,
});
//# sourceMappingURL=genkit.config.js.map