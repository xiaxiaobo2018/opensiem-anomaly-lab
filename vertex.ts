import { GoogleGenAI } from "@google/genai";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

const ai = new GoogleGenAI({
  vertexai: true,
  project: process.env.GOOGLE_CLOUD_PROJECT,
  location: process.env.GOOGLE_CLOUD_LOCATION || "global",
});

const chat = ai.chats.create({ model: "gemini-2.5-flash" });
const rl = readline.createInterface({ input, output });

async function main() {
  console.log("Type 'exit' to quit.");
  while (true) {
    const message = (await rl.question("You> ")).trim();
    if (message === "exit" || message === "quit") break;

    const response = await chat.sendMessage({ message });
    console.log("Gemini>", response.text);
  }
  rl.close();
}

main().catch(console.error);
