import { Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Editor from './pages/Editor';
import Audit from './pages/Audit'; // NEW

function App() {
  return (
    <div className="min-h-screen">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/editor/:id" element={<Editor />} />
        <Route path="/audit" element={<Audit />} /> {/* NEW */}
      </Routes>
    </div>
  );
}
export default App;