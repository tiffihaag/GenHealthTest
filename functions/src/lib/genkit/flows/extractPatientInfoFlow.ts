import {defineFlow} from "@genkit-ai/flow";
import {generate} from "@genkit-ai/ai";
import {gemini15Flash} from "@genkit-ai/vertexai";
import * as z from "zod";
import { getRegistry } from "@genkit-ai/core/registry";

const PatientSchema = z.object({
  firstName: z.string().nullable(),
  lastName: z.string().nullable(),
  dob: z.string().nullable(),
});

export const extractPatientInfoFlow = defineFlow(
  {
    name: "extractPatientInfoFlow",
    inputSchema: z.object({pdf_text: z.string()}),
    outputSchema: PatientSchema,
  },
  async (input) => {
    const pdfText = input.pdf_text;
    const prompt =
      `Extract the patient's first name, last name, and date of birth.

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

    const llmResponse = await generate({
    const llmResponse = await generate(getRegistry(), {
      prompt: prompt,
      model: gemini15Flash,
      output: {schema: PatientSchema},
    });
    return llmResponse.output() || {firstName: null, lastName: null, dob: null};
  }
);