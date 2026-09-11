import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { filesystemAPI, DiskSpaceResponse } from '../services/api';

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 GB';
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1000) return `${(gb / 1024).toFixed(2)} TB`;
  return `${gb.toFixed(1)} GB`;
};

const RADIUS = 70;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const DiskSpaceChart: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['disk-space'],
    queryFn: () => filesystemAPI.getDiskSpace().then(res => res.data as DiskSpaceResponse),
  });

  if (isLoading) {
    return (
      <div className="glass rounded-2xl p-6 animate-shimmer h-64" />
    );
  }

  if (isError || !data || data.disks_count === 0) {
    return (
      <div className="glass rounded-2xl p-6">
        <p className="text-center text-muted-foreground text-sm">
          {isError
            ? 'Erro ao carregar informações do disco'
            : 'Nenhum caminho de mídia configurado'}
        </p>
      </div>
    );
  }

  const usedRatio = data.total_bytes > 0 ? data.used_bytes / data.total_bytes : 0;

  return (
    <div className="glass rounded-2xl p-6">
      <h3 className="font-display text-lg font-bold text-foreground mb-4">
        Espaço em Disco
      </h3>
      <div className="relative flex items-center justify-center">
        <svg viewBox="0 0 200 200" className="w-[200px] h-[200px]" role="img" aria-label="Uso do disco">
          <circle
            cx="100"
            cy="100"
            r={RADIUS}
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth="20"
          />
          <circle
            cx="100"
            cy="100"
            r={RADIUS}
            fill="none"
            stroke="#ef4444"
            strokeWidth="20"
            strokeDasharray={`${usedRatio * CIRCUMFERENCE} ${CIRCUMFERENCE}`}
            transform="rotate(-90 100 100)"
          />
          <circle
            cx="100"
            cy="100"
            r={RADIUS}
            fill="none"
            stroke="#22c55e"
            strokeWidth="20"
            strokeDasharray={`${(1 - usedRatio) * CIRCUMFERENCE} ${CIRCUMFERENCE}`}
            transform={`rotate(${usedRatio * 360 - 90} 100 100)`}
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <p className="text-2xl font-bold text-foreground">
            {formatBytes(data.free_bytes)}
          </p>
          <p className="text-xs text-muted-foreground">
            livres de {formatBytes(data.total_bytes)}
          </p>
        </div>
      </div>
      <div className="flex justify-center gap-6 mt-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-sm text-muted-foreground">Usado</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-sm text-muted-foreground">Livre</span>
        </div>
      </div>
    </div>
  );
};

export default DiskSpaceChart;
