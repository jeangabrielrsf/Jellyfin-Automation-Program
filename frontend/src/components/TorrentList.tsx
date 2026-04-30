import React from 'react';
import { Download, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
import { TorrentResult } from '../types';

interface TorrentListProps {
  torrents: TorrentResult[];
  onDownload: (torrent: TorrentResult) => void;
}

export const TorrentList: React.FC<TorrentListProps> = ({ torrents, onDownload }) => {
  if (torrents.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
          <Download className="w-8 h-8 text-muted-foreground/50" />
        </div>
        <p className="text-lg font-medium">Nenhum torrent encontrado</p>
        <p className="text-sm mt-1">Tente buscar com termos diferentes</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {torrents.map((torrent, index) => (
        <div
          key={index}
          className="group flex items-center gap-4 p-4 rounded-xl
                    glass hover:border-primary/20
                    transition-all duration-300 hover:-translate-y-0.5"
          style={{ animationDelay: `${index * 50}ms` }}
        >
          <div className="flex-1 min-w-0">
            <h4 className="font-body font-semibold text-foreground truncate mb-2">
              {torrent.title}
            </h4>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
              <span className="font-mono text-xs">{torrent.indexer}</span>
              <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
              <span className="font-mono text-xs">{torrent.size}</span>
              <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
              <div className="flex items-center gap-1 text-emerald-500">
                <ArrowUpCircle className="w-3.5 h-3.5" />
                <span className="font-mono font-medium">{torrent.seeds}</span>
              </div>
              <div className="flex items-center gap-1 text-sky-500">
                <ArrowDownCircle className="w-3.5 h-3.5" />
                <span className="font-mono font-medium">{torrent.peers}</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {torrent.quality && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                              bg-primary/10 text-primary border border-primary/20">
                  {torrent.quality}
                </span>
              )}
              {torrent.language && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                              bg-muted text-muted-foreground border border-border">
                  {torrent.language}
                </span>
              )}
              {torrent.release_group && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                              bg-muted text-muted-foreground border border-border">
                  {torrent.release_group}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => onDownload(torrent)}
            className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground
                     font-medium text-sm
                     hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                     active:scale-[0.98]
                     transition-all duration-200 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Baixar</span>
          </button>
        </div>
      ))}
    </div>
  );
};
