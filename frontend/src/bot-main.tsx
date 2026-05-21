import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import BotApp from "./BotApp";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BotApp />
  </StrictMode>
);
