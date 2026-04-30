import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DownloadMonitor } from '../components/DownloadMonitor';
import { downloadAPI } from '../services/api';

const DownloadsPage: React.FC = () => {
  const { data: downloads, isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: () => downloadAPI.listDownloads(),
    refetchInterval: 5000,
  });

  const handlePause = (id: number) => {
    console.log('Pause:', id);
  };

  const handleResume = (id: number) => {
    console.log('Resume:', id);
  };

  const handleCancel = (id: number) => {
    console.log('Cancel:', id);
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
