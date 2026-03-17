import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import HistoryPage from './pages/History';

export default function App() {
  return (
    <BrowserRouter>
      <div className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/history/:agent" element={<HistoryPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
