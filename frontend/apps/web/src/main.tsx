import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { router } from "./router/router";
import { queryClient } from "./lib/queryClient";
import "./index.css";

// Offline detection
window.addEventListener("online",  () =>
  window.dispatchEvent(new CustomEvent("pos:online")));
window.addEventListener("offline", () =>
  window.dispatchEvent(new CustomEvent("pos:offline")));

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);