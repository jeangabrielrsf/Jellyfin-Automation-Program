import React from 'react';
import { Download } from '../types';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { Pause, Play, Trash2 } from 'lucide-react';
import { Button } from './ui/button';

interface DownloadMonitorProps {
  downloads: Download[];
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onCancel: (id: number) => void;
}

export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
}) => {
  if (downloads.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Nenhum download ativo
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'downloading': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'cancelled': return 'bg-gray-500';
      default: return 'bg-yellow-500';
    }
  };

  return (
    <div className="space-y-4">
      {downloads.map((download) => (
        <div key={download.id} className="border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium">{download.title}</h4>
            <Badge className={getStatusColor(download.status)}>
              {download.status}
            </Badge>
          </div>
          
          <Progress value={download.progress * 100} className="mb-2" />
          
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div className="flex gap-4">
              <span>{(download.progress * 100).toFixed(1)}%</span>
              {download.speed && <span>{download.speed}</span>}
              {download.eta && <span>ETA: {download.eta}</span>}
            </div>
            
            <div className="flex gap-2">
              {download.status === 'downloading' && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onPause(download.id)}
                >
                  <Pause className="w-4 h-4" />
                </Button>
              )}
              {download.status === 'paused' && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onResume(download.id)}
                >
                  <Play className="w-4 h-4" />
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() => onCancel(download.id)}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
