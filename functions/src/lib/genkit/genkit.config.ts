import {vertexAI} from "@genkit-ai/vertexai";
import {configureGenkit} from "@genkit-ai/core";
import {firebase} from "@genkit-ai/firebase";

export default configureGenkit({
  plugins: [
    firebase(),
    vertexAI({location: "us-central1"}),
  ],
  logLevel: "debug",
});