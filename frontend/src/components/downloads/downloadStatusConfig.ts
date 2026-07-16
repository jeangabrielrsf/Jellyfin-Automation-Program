import React from 'react';
import { Pause, Trash2, Download, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

export const downloadStatusConfig: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  downloading: { icon: Download, color: 'text-sky-400', bg: 'bg-sky-400/10', label: 'Baixando' },
  completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: 'Concluído' },
  organized: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: 'Organizado' },
  failed: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Falhou' },
  cancelled: { icon: Trash2, color: 'text-muted-foreground', bg: 'bg-muted', label: 'Cancelado' },
  paused: { icon: Pause, color: 'text-amber-400', bg: 'bg-amber-400/10', label: 'Pausado' },
  pending: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-400/10', label: 'Na fila' },
};
