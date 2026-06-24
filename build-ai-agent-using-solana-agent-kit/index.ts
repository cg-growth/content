import { initializeAgent, solanaKit } from "./agent";
import { HumanMessage } from "@langchain/core/messages";
import readline from "readline";

// Create a readline interface for interactive CLI
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const initializeChat = async () => {
  const agent = await initializeAgent();
  const config = { configurable: { thread_id: "Solana Agent Kit!" } };

  console.log("Chat session started. Type 'exit' to quit.");

  while (true) {
    const userQuestion = await new Promise<string>((resolve) => {
      rl.question("You: ", resolve);
    });

    if (userQuestion.toLowerCase() === "exit") {
      console.log("Exiting chat session...");
      rl.close();
      break;
    }

    // Send the user's message to the agent and display the response
    try {
      const stream = await agent.stream(
        {
          messages: [new HumanMessage(userQuestion)],
        },
        config
      );

      // Handle the response from the agent
      for await (const chunk of stream) {
        if ("agent" in chunk) {
          console.log("Agent:", chunk.agent.messages[0].content);
        } else if ("tools" in chunk) {
          console.log("Tools:", chunk.tools.messages[0].content);
        }
      }
    } catch (error) {
      console.error("Error during chat interaction:", error);
    }
  }
};

// Command-line interface to decide between chatting or fetching token info
const program = async () => {
  console.log("Welcome to the Solana Agent Chat CLI.");
  initializeChat();
};

// Start the program
program();
