import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import BotDocsApp from "@/BotDocsApp";
import "@/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BotDocsApp />
  </StrictMode>
);
