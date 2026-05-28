import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TeamWeek from "./pages/TeamWeek";
import Dynamics from "./pages/Dynamics";
import ClientHeatmap from "./pages/ClientHeatmap";
import VacationCalendar from "./pages/VacationCalendar";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<TeamWeek />} />
            <Route path="/dynamics" element={<Dynamics />} />
            <Route path="/clients" element={<ClientHeatmap />} />
            <Route path="/vacations" element={<VacationCalendar />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}