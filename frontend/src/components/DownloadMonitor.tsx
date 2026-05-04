import React, { useState } from 'react';
import { Pause, Play, Trash2, Download, CheckCircle2, AlertCircle, Clock, Info } from 'lucide-react';
import { Download as DownloadType } from '../types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

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
  pending: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-400/10', label: 'Na fila' },
};

export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
}) => {
  const [selectedDownload, setSelectedDownload] = useState<DownloadType | null>(null);

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
        const status = statusConfig[download.status] || statusConfig.pending;
        const StatusIcon = status.icon;
        const progress = Math.round(download.progress * 100);
        const hasDetails = download.status === 'failed' || download.error_message;

        return (
          <div
            key={download.id}
            onClick={() => hasDetails && setSelectedDownload(download)}
            className={`glass rounded-2xl p-5 transition-all duration-300
                     hover:border-primary/20 hover:-translate-y-0.5
                     ${hasDetails ? 'cursor-pointer' : ''}`}
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
                    {hasDetails && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Info className="w-3 h-3" />
                        Clique para detalhes
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {download.status === 'downloading' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onPause(download.id); }}
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
                    onClick={(e) => { e.stopPropagation(); onResume(download.id); }}
                    className="w-9 h-9 rounded-lg glass flex items-center justify-center
                             hover:bg-emerald-400/10 hover:text-emerald-400
                             active:scale-95 transition-all duration-200"
                    title="Retomar"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); onCancel(download.id); }}
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

      {/* Detail Dialog */}
      <Dialog open={!!selectedDownload} onOpenChange={(open) => !open && setSelectedDownload(null)}>
        <DialogContent className="glass rounded-2xl p-6 max-w-lg w-full space-y-4 border-none">
          <DialogHeader>
            <DialogTitle className="font-display text-xl font-bold text-foreground">
              Detalhes do Download
            </DialogTitle>
          </DialogHeader>

          {selectedDownload && (
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-muted-foreground">Título:</span>
                <p className="font-semibold text-foreground">{selectedDownload.title}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Torrent:</span>
                <p className="font-mono text-foreground text-xs break-all">{selectedDownload.torrent_name || '—'}</p>
              </div>
              <div className="flex gap-4">
                <div>
                  <span className="text-muted-foreground">Status:</span>
                  <p className="font-semibold text-foreground capitalize">{selectedDownload.status}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Qualidade:</span>
                  <p className="font-semibold text-foreground">{selectedDownload.quality}</p>
                </div>
              </div>
              {selectedDownload.magnet_link && (
                <div>
                  <span className="text-muted-foreground">Link/Magnet:</span>
                  <p className="font-mono text-foreground text-xs break-all bg-muted/50 rounded-lg p-2 mt-1">
                    {selectedDownload.magnet_link}
                  </p>
                </div>
              )}
              {selectedDownload.error_message && (
                <div className="rounded-xl bg-red-400/10 border border-red-400/20 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="w-4 h-4 text-red-400" />
                    <span className="font-semibold text-red-400">Erro</span>
                  </div>
                  <p className="text-red-300 text-sm whitespace-pre-wrap">
                    {selectedDownload.error_message}
                  </p>
                </div>
              )}
              <div>
                <span className="text-muted-foreground">Criado em:</span>
                <p className="text-foreground">
                  {new Date(selectedDownload.created_at).toLocaleString('pt-BR')}
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
