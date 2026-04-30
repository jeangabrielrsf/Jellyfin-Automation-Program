import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Search, Download, Settings, Home, FileText } from 'lucide-react';
import HomePage from './pages/Home';
import SearchPage from './pages/Search';
import DownloadsPage from './pages/Downloads';
import SettingsPage from './pages/Settings';
import LogsPage from './pages/Logs';

function App() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', icon: Home, label: 'Início' },
    { path: '/search', icon: Search, label: 'Buscar' },
    { path: '/downloads', icon: Download, label: 'Downloads' },
    { path: '/settings', icon: Settings, label: 'Configurações' },
    { path: '/logs', icon: FileText, label: 'Logs' },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">Jellyfin Automation</h1>
          <nav className="flex gap-4">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-3 py-2 rounded-md transition-colors ${
                  location.pathname === item.path
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-accent'
                }`}
              >
                <item.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
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
