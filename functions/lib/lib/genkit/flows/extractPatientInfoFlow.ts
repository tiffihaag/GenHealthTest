"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.extractPatientInfoFlow = void 0;
const flow_1 = require("@genkit-ai/flow");
const core_1 = require("@genkit-ai/core");
const vertexai_1 = require("@genkit-ai/vertexai");
const z = __importStar(require("zod"));
const PatientSchema = z.object({
    firstName: z.string().nullable(),
    lastName: z.string().nullable(),
    dob: z.string().nullable(),
});
exports.extractPatientInfoFlow = (0, flow_1.defineFlow)({
    name: "extractPatientInfoFlow",
    inputSchema: z.object({ pdf_text: z.string() }),
    outputSchema: PatientSchema,
}, async (input) => {
    const pdfText = input.pdf_text;
    // This prompt now correctly uses the `pdfText` variable.
    const prompt = `Extract the patient's first name, last name, and date of birth.

Instructions:
- If information is not confidently identified, return null.
- Date of birth format is MM/DD/YYYY.
- Only extract clearly information.
- Only output the requested JSON object. 

Document Text:
---
${pdfText}
---

Please provide the extracted information in a JSON object.`;
    const llmResponse = await (0, core_1.generate)({
        prompt: prompt,
        model: vertexai_1.gemini15Flash,
        output: { schema: PatientSchema },
    });
    return llmResponse.output() || { firstName: null, lastName: null, dob: null };
});
//# sourceMappingURL=extractPatientInfoFlow.js.map