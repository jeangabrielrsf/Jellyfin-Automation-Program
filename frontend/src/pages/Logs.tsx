import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Input } from '../components/ui/input';
import { logsAPI } from '../services/api';

const LogsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [level, setLevel] = useState('');

  const { data: logs, isLoading } = useQuery({
    queryKey: ['logs', level, search],
    queryFn: () => logsAPI.getLogs({ level, search }),
  });

  if (isLoading) {
    return <div className="text-center py-8">Carregando logs...</div>;
  }

  const logLines = logs?.data?.logs || [];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Logs</h2>
      
      <div className="flex gap-2">
        <Input
          placeholder="Filtrar logs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="border rounded-md px-3"
          value={level}
          onChange={(e) => setLevel(e.target.value)}
        >
          <option value="">Todos</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
      </div>

      <div className="border rounded-md p-4 bg-muted font-mono text-sm h-[600px] overflow-auto">
        {logLines.length === 0 ? (
          <div className="text-muted-foreground">Nenhum log encontrado</div>
        ) : (
          logLines.map((line: string, index: number) => (
            <div key={index} className="py-1">
              {line}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default LogsPage;
