import React from 'react';
import { Pause, Play, Trash2, Download, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { Download as DownloadType } from '../types';

interface DownloadMonitorProps {
  downloads: DownloadType[];
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onCancel: (id: number) => void;
}

const statusConfig: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  downloading: { icon: Download, color: 'text-sky-400', bg: 'bg-sky-400/10', label: 'Baixando' },
  completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: 'Concluído' },
  failed: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Falhou' },
  cancelled: { icon: Trash2, color: 'text-muted-foreground', bg: 'bg-muted', label: 'Cancelado' },
  paused: { icon: Pause, color: 'text-amber-400', bg: 'bg-amber-400/10', label: 'Pausado' },
  queued: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-400/10', label: 'Na fila' },
};

export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
}) => {
  if (downloads.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mx-auto mb-6">
          <Download className="w-10 h-10 text-muted-foreground/40" />
        </div>
        <p className="text-xl font-display font-bold mb-2">Nenhum download ativo</p>
        <p className="text-sm">Vá para a página de busca para adicionar downloads</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {downloads.map((download, index) => {
        const status = statusConfig[download.status] || statusConfig.queued;
        const StatusIcon = status.icon;
        const progress = Math.round(download.progress * 100);

        return (
          <div
            key={download.id}
            className="glass rounded-2xl p-5 transition-all duration-300
                     hover:border-primary/20 hover:-translate-y-0.5"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-10 h-10 rounded-xl ${status.bg} flex items-center justify-center flex-shrink-0`}>
                  <StatusIcon className={`w-5 h-5 ${status.color}`} />
                </div>
                <div className="min-w-0">
                  <h4 className="font-body font-semibold text-foreground truncate">
                    {download.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md ${status.bg} ${status.color}`}>
                      {status.label}
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      {download.quality || '1080p'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {download.status === 'downloading' && (
                  <button
                    onClick={() => onPause(download.id)}
                    className="w-9 h-9 rounded-lg glass flex items-center justify-center
                             hover:bg-amber-400/10 hover:text-amber-400
                             active:scale-95 transition-all duration-200"
                    title="Pausar"
                  >
                    <Pause className="w-4 h-4" />
                  </button>
                )}
                {download.status === 'paused' && (
                  <button
                    onClick={() => onResume(download.id)}
                    className="w-9 h-9 rounded-lg glass flex items-center justify-center
                             hover:bg-emerald-400/10 hover:text-emerald-400
                             active:scale-95 transition-all duration-200"
                    title="Retomar"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => onCancel(download.id)}
                  className="w-9 h-9 rounded-lg glass flex items-center justify-center
                           hover:bg-red-400/10 hover:text-red-400
                           active:scale-95 transition-all duration-200"
                  title="Cancelar"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Progress */}
            {download.status === 'downloading' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono font-semibold text-primary">{progress}%</span>
                  <div className="flex items-center gap-4 text-muted-foreground text-xs font-mono">
                    {download.speed && <span>{download.speed}</span>}
                    {download.eta && <span>ETA: {download.eta}</span>}
                  </div>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-primary to-orange-300
                             transition-all duration-500 ease-out relative"
                    style={{ width: `${progress}%` }}
                  >
                    {progress < 100 && (
                      <div className="absolute inset-0 animate-shimmer" />
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
