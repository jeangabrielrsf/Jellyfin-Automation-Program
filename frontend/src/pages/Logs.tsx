import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, FileText, AlertTriangle, Info, Bug, XCircle } from 'lucide-react';
import { logsAPI } from '../services/api';

const levelOptions = [
  { value: '', label: 'Todos', icon: FileText },
  { value: 'DEBUG', label: 'DEBUG', icon: Bug, color: 'text-muted-foreground' },
  { value: 'INFO', label: 'INFO', icon: Info, color: 'text-sky-400' },
  { value: 'WARNING', label: 'WARNING', icon: AlertTriangle, color: 'text-amber-400' },
  { value: 'ERROR', label: 'ERROR', icon: XCircle, color: 'text-red-400' },
];

const LogsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [level, setLevel] = useState('');

  const { data: logs, isLoading } = useQuery({
    queryKey: ['logs', level, search],
    queryFn: () => logsAPI.getLogs({ level, search }),
  });

  if (isLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">Logs</h2>
        </div>
        <div className="glass rounded-2xl p-4 h-[600px] animate-shimmer" />
      </div>
    );
  }

  const logLines = logs?.data?.logs || [];

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Logs
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Visualize e filtre os logs do sistema
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filtrar logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-11 pr-4 py-3 rounded-xl glass bg-transparent
                     border border-border/50
                     focus:outline-none focus:ring-2 focus:ring-primary/30
                     focus:border-primary/30
                     text-foreground placeholder:text-muted-foreground/50
                     text-sm transition-all duration-200"
          />
        </div>
        <div className="flex gap-2">
          {levelOptions.map((opt) => {
            const Icon = opt.icon;
            const isActive = level === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => setLevel(opt.value)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold uppercase tracking-wider
                          flex items-center gap-1.5 transition-all duration-200
                          ${isActive
                            ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20'
                            : 'glass text-muted-foreground hover:text-foreground hover:bg-accent'
                          }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Log Terminal */}
      <div className="glass rounded-2xl p-1 overflow-hidden">
        <div className="rounded-xl bg-black/90 dark:bg-black/90 bg-stone-900/95
                      p-4 font-mono text-sm h-[600px] overflow-auto">
          {logLines.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <FileText className="w-12 h-12 mb-4 opacity-30" />
              <p>Nenhum log encontrado</p>
            </div>
          ) : (
            <div className="space-y-1">
              {logLines.map((line: string, index: number) => (
                <div
                  key={index}
                  className="py-1 px-2 rounded hover:bg-white/5 transition-colors
                           text-stone-300 leading-relaxed break-all"
                >
                  {line}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
