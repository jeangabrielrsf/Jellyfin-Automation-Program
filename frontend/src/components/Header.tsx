import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Search, Download, Settings, Home, FileText, Play, Compass, Menu } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from '@/components/ui/sheet';

const navItems = [
  { path: '/', icon: Home, label: 'Início' },
  { path: '/discover', icon: Compass, label: 'Explorar' },
  { path: '/search', icon: Search, label: 'Buscar' },
  { path: '/downloads', icon: Download, label: 'Downloads' },
  { path: '/settings', icon: Settings, label: 'Configurações' },
  { path: '/logs', icon: FileText, label: 'Logs' },
];

export const Header: React.FC = () => {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-strong">
      <div className="container mx-auto px-4 sm:px-6 lg:px-12">
        <div className="flex items-center justify-between h-[72px]">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center
                          shadow-lg shadow-primary/20 group-hover:shadow-primary/40
                          transition-shadow duration-300">
              <Play className="w-5 h-5 text-primary-foreground fill-current" />
            </div>
            <span className="font-display text-xl font-bold text-gradient">
              Jellyfin Automation
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
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
                  <span>{item.label}</span>
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
            {/* Desktop: theme toggle + avatar */}
            <div className="hidden md:flex items-center gap-3">
              <ThemeToggle />
              <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20
                            flex items-center justify-center">
                <span className="text-sm font-semibold text-primary">JA</span>
              </div>
            </div>

            {/* Mobile: hamburger menu */}
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <button className="md:hidden w-9 h-9 rounded-xl glass flex items-center justify-center
                                 text-muted-foreground hover:text-foreground transition-colors">
                  <Menu className="w-5 h-5" />
                </button>
              </SheetTrigger>
              <SheetContent className="glass-strong">
                <div className="flex flex-col h-full">
                  <div className="flex items-center gap-3 mb-8 pt-2">
                    <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
                      <Play className="w-5 h-5 text-primary-foreground fill-current" />
                    </div>
                    <span className="font-display text-xl font-bold text-gradient">
                      Jellyfin Automation
                    </span>
                  </div>

                  <nav className="flex flex-col gap-1 flex-1">
                    {navItems.map((item) => {
                      const isActive = location.pathname === item.path;
                      return (
                        <Link
                          key={item.path}
                          to={item.path}
                          onClick={() => setOpen(false)}
                          className={`flex items-center gap-3 px-4 py-3 rounded-xl
                                    text-base font-medium font-body transition-all duration-300
                                    ${isActive
                                      ? 'text-primary bg-primary/10'
                                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                                    }`}
                        >
                          <item.icon className="w-5 h-5" />
                          <span>{item.label}</span>
                        </Link>
                      );
                    })}
                  </nav>

                  <div className="border-t border-border/30 pt-4 mt-4 space-y-4">
                    <div className="flex items-center justify-between px-4 py-2">
                      <span className="text-sm text-muted-foreground">Tema</span>
                      <ThemeToggle />
                    </div>
                    <div className="flex items-center gap-3 px-4 py-2">
                      <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20
                                    flex items-center justify-center">
                        <span className="text-sm font-semibold text-primary">JA</span>
                      </div>
                      <span className="text-sm font-medium text-foreground">Jellyfin Admin</span>
                    </div>
                  </div>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  );
};
