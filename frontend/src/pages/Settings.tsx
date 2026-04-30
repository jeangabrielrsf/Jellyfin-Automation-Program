import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { settingsAPI } from '../services/api';

const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: currentSettings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsAPI.getSettings(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: any }) =>
      settingsAPI.updateSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleUpdate = (key: string, value: any) => {
    updateMutation.mutate({ key, value });
  };

  if (isLoading) {
    return <div className="text-center py-8">Carregando configurações...</div>;
  }

  const settingKeys = [
    { key: 'movies_path', label: 'Pasta de Filmes', type: 'text' },
    { key: 'series_path', label: 'Pasta de Séries', type: 'text' },
    { key: 'animes_path', label: 'Pasta de Animes', type: 'text' },
    { key: 'default_quality', label: 'Qualidade Padrão', type: 'text' },
    { key: 'default_language', label: 'Idioma Padrão', type: 'text' },
  ];

  const currentValues = currentSettings?.data || {};

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Configurações</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {settingKeys.map((setting) => (
          <Card key={setting.key}>
            <CardHeader>
              <CardTitle className="text-lg">{setting.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  defaultValue={currentValues[setting.key] || ''}
                  placeholder={`Digite ${setting.label.toLowerCase()}`}
                  onBlur={(e) => {
                    if (e.target.value) {
                      handleUpdate(setting.key, e.target.value);
                    }
                  }}
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default SettingsPage;
