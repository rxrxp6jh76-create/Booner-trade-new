import { useState, useEffect, Component } from "react";
import "@/App.css";
import { HashRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import { Toaster } from "./components/ui/sonner";

// V2.3.32: Error Boundary um Runtime Errors abzufangen
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('🚨 Runtime Error gefangen:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-900 flex items-center justify-center p-8">
          <div className="bg-slate-800 rounded-lg p-8 max-w-lg text-center">
            <h1 className="text-2xl font-bold text-red-400 mb-4">⚠️ Runtime Error</h1>
            <p className="text-slate-300 mb-4">
              Ein unerwarteter Fehler ist aufgetreten. Bitte laden Sie die Seite neu.
            </p>
            <div className="bg-slate-700 rounded p-3 text-left text-sm text-slate-400 mb-4 max-h-40 overflow-auto">
              <code>{this.state.error?.toString()}</code>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg"
            >
              🔄 Seite neu laden
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <div className="App">
      <Toaster position="top-right" />
      <ErrorBoundary>
        <HashRouter>
          <Routes>
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </HashRouter>
      </ErrorBoundary>
    </div>
  );
}

export default App;