import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DownloadMonitor } from '../components/DownloadMonitor';
import { downloadAPI } from '../services/api';

const DownloadsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: downloads, isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: () => downloadAPI.listDownloads(),
    refetchInterval: 5000,
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

  const handlePause = (id: number) => {
    pauseMutation.mutate(id);
  };

  const handleResume = (id: number) => {
    resumeMutation.mutate(id);
  };

  const handleCancel = (id: number) => {
    if (window.confirm('Tem certeza que deseja cancelar este download?')) {
      cancelMutation.mutate(id);
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">Carregando downloads...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Downloads</h2>
      <DownloadMonitor
        downloads={downloads?.data || []}
        onPause={handlePause}
        onResume={handleResume}
        onCancel={handleCancel}
      />
    </div>
  );
};

export default DownloadsPage;
