import { useState, useEffect } from "react";
import "@/App.css";
import { HashRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import { Toaster } from "./components/ui/sonner";

function App() {
  return (
    <div className="App">
      <Toaster position="top-right" />
      <HashRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </HashRouter>
    </div>
  );
}

export default App;