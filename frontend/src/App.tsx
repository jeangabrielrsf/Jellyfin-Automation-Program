import { Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import HomePage from './pages/Home';
import SearchPage from './pages/Search';
import DownloadsPage from './pages/Downloads';
import SettingsPage from './pages/Settings';
import LogsPage from './pages/Logs';

function App() {
  return (
    <div className="min-h-screen bg-background font-body">
      <Header />
      <main className="container mx-auto px-6 lg:px-12 pt-24 pb-16">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/downloads" element={<DownloadsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/logs" element={<LogsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
