/**
 * See https://firebase.google.com/docs/functions/typescript
 */
import { onCall } from "firebase-functions/v2/https";
import { runFlow } from "@genkit-ai/flow";
import "./lib/genkit/genkit.config.js";
import { extractPatientInfoFlow } from "./lib/genkit/flows/extractPatientInfoFlow.js";

// Export the Genkit flow as a Firebase Function.
export const extractPatientInfo = onCall(async (request) => {
  const flowResult = await runFlow(extractPatientInfoFlow, request.data);
  return flowResult;
});
