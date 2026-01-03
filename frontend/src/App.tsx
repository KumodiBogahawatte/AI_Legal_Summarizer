import React from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useLocation,
} from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import CaseAnalysis from "./pages/CaseAnalysis";
import "./App.css";

function NavigationBar() {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-content">
        <Link to="/" className="navbar-brand">
          ⚖️ AI Legal Summarizer
        </Link>
        <div className="navbar-links">
          <Link to="/" className={location.pathname === "/" ? "active" : ""}>
            Home
          </Link>
          <Link
            to="/analyze"
            className={location.pathname === "/analyze" ? "active" : ""}
          >
            Case Analysis
          </Link>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <NavigationBar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard lang="en" />} />
            <Route path="/analyze" element={<CaseAnalysis lang="en" />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
