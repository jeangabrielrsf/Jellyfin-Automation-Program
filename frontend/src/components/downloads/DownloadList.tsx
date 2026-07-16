import React from 'react';
import { Pause, Play, Trash2, Info } from 'lucide-react';
import type { Download as DownloadType } from '@/types';
import { downloadStatusConfig } from './downloadStatusConfig';

interface DownloadListProps {
  downloads: DownloadType[];
  onSelectDownload: (download: DownloadType) => void;
  onRequestCancel: (download: DownloadType) => void;
  onPause: (id: number) => void;
  onResume: (id: number) => void;
}

export const DownloadList: React.FC<DownloadListProps> = ({
  downloads,
  onSelectDownload,
  onRequestCancel,
  onPause,
  onResume,
}) => {
  return (
    <>
      {downloads.map((download, index) => {
        const status = downloadStatusConfig[download.status] || downloadStatusConfig.pending;
        const StatusIcon = status.icon;
        const progress = Math.round(download.progress * 100);

        return (
          <div
            key={download.id}
            onClick={() => onSelectDownload(download)}
            className="glass rounded-2xl p-5 transition-all duration-300
                     hover:border-primary/20 hover:-translate-y-0.5 cursor-pointer"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
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
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Info className="w-3 h-3" />
                      Clique para detalhes
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0 sm:self-auto self-end">
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
                  onClick={(e) => { e.stopPropagation(); onRequestCancel(download); }}
                  className="w-9 h-9 rounded-lg glass flex items-center justify-center
                           hover:bg-red-400/10 hover:text-red-400
                           active:scale-95 transition-all duration-200"
                  title="Cancelar"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

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
    </>
  );
};
