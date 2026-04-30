import React from 'react';
import { TorrentResult } from '../types';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Download } from 'lucide-react';

interface TorrentListProps {
  torrents: TorrentResult[];
  onDownload: (torrent: TorrentResult) => void;
}

export const TorrentList: React.FC<TorrentListProps> = ({ torrents, onDownload }) => {
  if (torrents.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Nenhum torrent encontrado
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {torrents.map((torrent, index) => (
        <div
          key={index}
          className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
        >
          <div className="flex-1 min-w-0 mr-4">
            <h4 className="font-medium truncate">{torrent.title}</h4>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <span>{torrent.indexer}</span>
              <span>•</span>
              <span>{torrent.size}</span>
              <span>•</span>
              <span className="text-green-600">↑ {torrent.seeds}</span>
              <span className="text-blue-600">↓ {torrent.peers}</span>
            </div>
            <div className="flex gap-2 mt-2">
              {torrent.quality && (
                <Badge variant="outline">{torrent.quality}</Badge>
              )}
              {torrent.language && (
                <Badge variant="secondary">{torrent.language}</Badge>
              )}
              {torrent.release_group && (
                <Badge variant="outline">{torrent.release_group}</Badge>
              )}
            </div>
          </div>
          <Button
            size="sm"
            onClick={() => onDownload(torrent)}
          >
            <Download className="w-4 h-4 mr-2" />
            Baixar
          </Button>
        </div>
      ))}
    </div>
  );
};
