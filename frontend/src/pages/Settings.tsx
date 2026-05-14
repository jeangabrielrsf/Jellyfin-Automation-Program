import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Folder, Sparkles, Save } from 'lucide-react';
import { settingsAPI } from '../services/api';
import { Button } from '@/components/ui/button';
import FolderPickerDialog from '@/components/FolderPickerDialog';

const settingGroups = [
  {
    icon: Folder,
    title: 'Caminhos',
    description: 'Diretórios onde o conteúdo será salvo',
    settings: [
      { key: 'movies_path', label: 'Pasta de Filmes', placeholder: '/media/movies' },
      { key: 'series_path', label: 'Pasta de Séries', placeholder: '/media/series' },
      { key: 'animes_path', label: 'Pasta de Animes', placeholder: '/media/animes' },
    ],
  },
  {
    icon: Sparkles,
    title: 'Preferências',
    description: 'Configurações padrão para novos downloads',
    settings: [
      { key: 'default_quality', label: 'Qualidade Padrão', placeholder: '1080p' },
      { key: 'default_language', label: 'Idioma Padrão', placeholder: 'legendado' },
    ],
  },
];

const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [pickerOpen, setPickerOpen] = useState<string | null>(null);
  const [pathValues, setPathValues] = useState<Record<string, string>>({});

  const { data: currentSettings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsAPI.getSettings(),
  });

  const currentValues = currentSettings?.data || {};

  useEffect(() => {
    if (currentSettings?.data) {
      const newValues = {
        movies_path: currentSettings.data.movies_path || '',
        series_path: currentSettings.data.series_path || '',
        animes_path: currentSettings.data.animes_path || '',
      };
      setPathValues((prev) => {
        if (
          prev.movies_path === newValues.movies_path &&
          prev.series_path === newValues.series_path &&
          prev.animes_path === newValues.animes_path
        ) {
          return prev;
        }
        return { ...prev, ...newValues };
      });
    }
  }, [currentSettings?.data?.movies_path, currentSettings?.data?.series_path, currentSettings?.data?.animes_path]);

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      settingsAPI.updateSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleUpdate = (key: string, value: string) => {
    if (!value) return;

    // Update local state immediately for path inputs
    if (key in pathValues || key.endsWith('_path')) {
      setPathValues((prev) => ({ ...prev, [key]: value }));
    }
    updateMutation.mutate({ key, value });
  };

  if (isLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
            Configurações
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="glass rounded-2xl p-6 h-64 animate-shimmer" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Configurações
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Configure os caminhos de mídia e preferências de download
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {settingGroups.map((group) => (
          <div
            key={group.title}
            className="glass rounded-2xl p-6 space-y-6
                     transition-all duration-300 hover:border-primary/20"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <group.icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-display text-lg font-bold text-foreground">
                  {group.title}
                </h3>
                <p className="text-sm text-muted-foreground">{group.description}</p>
              </div>
            </div>

            <div className="space-y-4">
              {group.settings.map((setting) => (
                <div key={setting.key} className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    {setting.label}
                  </label>
                  <div className="relative group">
                    {setting.key === 'default_quality' ? (
                      <select
                        defaultValue={currentValues[setting.key] || '1080p'}
                        onChange={(e) => handleUpdate(setting.key, e.target.value)}
                        className="w-full px-4 py-3 rounded-xl glass bg-transparent
                                 border border-border/50
                                 focus:outline-none focus:ring-2 focus:ring-primary/30
                                 focus:border-primary/30
                                 text-foreground
                                 font-mono text-sm
                                 transition-all duration-200"
                      >
                        <option value="720p">720p</option>
                        <option value="1080p">1080p</option>
                        <option value="1440p">1440p</option>
                        <option value="2160p">2160p</option>
                      </select>
                    ) : setting.key === 'default_language' ? (
                      <select
                        defaultValue={currentValues[setting.key] || 'legendado'}
                        onChange={(e) => handleUpdate(setting.key, e.target.value)}
                        className="w-full px-4 py-3 rounded-xl glass bg-transparent
                                 border border-border/50
                                 focus:outline-none focus:ring-2 focus:ring-primary/30
                                 focus:border-primary/30
                                 text-foreground
                                 font-mono text-sm
                                 transition-all duration-200"
                      >
                        <option value="legendado">Legendado</option>
                        <option value="dublado">Dublado</option>
                      </select>
                    ) : (
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          type="text"
                          value={pathValues[setting.key] ?? currentValues[setting.key] ?? ''}
                          placeholder={setting.placeholder}
                          onChange={(e) => setPathValues((prev) => ({ ...prev, [setting.key]: e.target.value }))}
                          onBlur={(e) => handleUpdate(setting.key, e.target.value)}
                          className="flex-1 px-4 py-3 rounded-xl glass bg-transparent
                                   border border-border/50
                                   focus:outline-none focus:ring-2 focus:ring-primary/30
                                   focus:border-primary/30
                                   text-foreground placeholder:text-muted-foreground/50
                                   font-mono text-sm
                                   transition-all duration-200"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="default"
                          className="shrink-0 sm:w-auto w-full"
                          onClick={() => setPickerOpen(setting.key)}
                        >
                          <Folder className="w-4 h-4 mr-1" />
                          Browse
                        </Button>
                      </div>
                    )}
                    {updateMutation.isPending && updateMutation.variables?.key === setting.key && (
                      <Save className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary animate-pulse" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {pickerOpen && (
        <FolderPickerDialog
          open={!!pickerOpen}
          onOpenChange={(open) => {
            if (!open) setPickerOpen(null);
          }}
          onSelect={(path) => {
            handleUpdate(pickerOpen, path);
          }}
        />
      )}
    </div>
  );
};

export default SettingsPage;
