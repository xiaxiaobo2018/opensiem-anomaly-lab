import { GoogleGenAI } from "@google/genai";
import { execFileSync } from "node:child_process";

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function resolveProject() {
  if (process.env.GOOGLE_CLOUD_PROJECT) {
    return process.env.GOOGLE_CLOUD_PROJECT;
  }
  const output = execFileSync("gcloud", ["config", "get-value", "project"], {
    encoding: "utf8",
  }).trim();
  if (!output || output === "(unset)") {
    throw new Error("Could not resolve a Google Cloud project from env or gcloud config.");
  }
  return output;
}

async function main() {
  const rawInput = (await readStdin()).trim();
  if (!rawInput) {
    throw new Error("Expected JSON payload on stdin.");
  }

  const payload = JSON.parse(rawInput);
  const project = payload.project || resolveProject();
  const location = payload.location || process.env.GOOGLE_CLOUD_LOCATION || "global";
  const model = payload.model || "gemini-2.5-flash";
  const prompt = payload.prompt;

  if (!prompt) {
    throw new Error("Missing prompt in payload.");
  }

  const ai = new GoogleGenAI({
    vertexai: true,
    project,
    location,
    apiVersion: "v1",
  });

  const response = await ai.models.generateContent({
    model,
    contents: prompt,
    config: {
      temperature: 0.2,
    },
  });

  process.stdout.write(`${JSON.stringify({ text: response.text })}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});
