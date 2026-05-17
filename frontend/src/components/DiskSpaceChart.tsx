import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { filesystemAPI, DiskSpaceResponse } from '../services/api';

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 GB';
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1000) return `${(gb / 1024).toFixed(2)} TB`;
  return `${gb.toFixed(1)} GB`;
};

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

  const chartData = [
    { name: 'Usado', value: data.used_bytes },
    { name: 'Livre', value: data.free_bytes },
  ];

  const COLORS = ['#ef4444', '#22c55e'];

  return (
    <div className="glass rounded-2xl p-6">
      <h3 className="font-display text-lg font-bold text-foreground mb-4">
        Espaço em Disco
      </h3>
      <div className="flex items-center justify-center">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {chartData.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: unknown) => typeof value === 'number' ? formatBytes(value) : String(value)}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
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
