import React from 'react';
import { toast } from 'sonner';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DownloadMonitor } from '../components/DownloadMonitor';
import { downloadAPI } from '../services/api';
import { DownloadUpdates } from '../hooks/useDownloadUpdates';

const DownloadsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: downloads, isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: () => downloadAPI.listDownloads(),
  });

  const pauseMutation = useMutation({
    mutationFn: (id: number) => downloadAPI.pauseDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['downloads'] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => downloadAPI.resumeDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['downloads'] }),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => downloadAPI.cancelDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['downloads'] }),
  });

  const clearMutation = useMutation({
    mutationFn: () => downloadAPI.clearDownloads(),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      const result = response.data as { deleted: number; skipped: number };
      toast.success(`${result.deleted} download(s) removido(s)`);
    },
    onError: () => {
      toast.error('Erro ao limpar downloads');
    },
  });

  const handleClear = () => clearMutation.mutate();

  const handlePause = (id: number) => pauseMutation.mutate(id);
  const handleResume = (id: number) => resumeMutation.mutate(id);
  const handleCancel = (id: number) => {
    if (window.confirm('Tem certeza que deseja cancelar este download?')) {
      cancelMutation.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
            Downloads
          </h2>
          <p className="text-muted-foreground">Gerencie seus downloads ativos</p>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass rounded-2xl p-5 h-32 animate-shimmer" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <DownloadUpdates />
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Downloads
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Monitore e gerencie todos os seus downloads em tempo real
        </p>
      </div>

      <DownloadMonitor
        downloads={downloads?.data || []}
        onPause={handlePause}
        onResume={handleResume}
        onCancel={handleCancel}
        onClear={handleClear}
      />
    </div>
  );
};

export default DownloadsPage;
