import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Search, Download, Settings, Home, FileText, Play } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';

const navItems = [
  { path: '/', icon: Home, label: 'Início' },
  { path: '/search', icon: Search, label: 'Buscar' },
  { path: '/downloads', icon: Download, label: 'Downloads' },
  { path: '/settings', icon: Settings, label: 'Configurações' },
  { path: '/logs', icon: FileText, label: 'Logs' },
];

export const Header: React.FC = () => {
  const location = useLocation();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-strong">
      <div className="container mx-auto px-6 lg:px-12">
        <div className="flex items-center justify-between h-[72px]">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center
                          shadow-lg shadow-primary/20 group-hover:shadow-primary/40
                          transition-shadow duration-300">
              <Play className="w-5 h-5 text-primary-foreground fill-current" />
            </div>
            <span className="font-display text-xl font-bold text-gradient hidden sm:block">
              Jellyfin Automation
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-2 px-4 py-2 rounded-xl
                            text-sm font-medium font-body transition-all duration-300
                            ${isActive
                              ? 'text-primary bg-primary/10'
                              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                            }`}
                >
                  <item.icon className={`w-4 h-4 transition-transform duration-300
                                        ${isActive ? '' : 'group-hover:-translate-y-0.5'}`} />
                  <span className="hidden md:inline">{item.label}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5
                                   rounded-full bg-primary" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20
                          flex items-center justify-center">
              <span className="text-sm font-semibold text-primary">JA</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
