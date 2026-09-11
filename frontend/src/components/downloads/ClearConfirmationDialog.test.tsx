import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AxiosResponse } from 'axios';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClearConfirmationDialog } from './ClearConfirmationDialog';
import { Button } from '@/components/ui/button';
import type { Download } from '@/types';

vi.mock('@/services/api', () => ({
  downloadAPI: {
    getClearableDownloads: vi.fn(),
  },
}));

import { downloadAPI } from '@/services/api';

const mockedGetClearable = vi.mocked(downloadAPI.getClearableDownloads);

function makeDownload(id: number, title: string): Download {
  return {
    id,
    tmdb_id: id,
    title,
    type: 'movie',
    quality: '1080p',
    language_preference: 'Legendado',
    status: 'completed',
    progress: 1,
    created_at: '2024-01-15T10:00:00Z',
  };
}

const downloads = [makeDownload(1, 'Movie One'), makeDownload(2, 'Movie Two')];

function renderDialog(props: Record<string, unknown> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ClearConfirmationDialog clearableCount={2} onClear={vi.fn()} {...props}>
        <Button>Limpar todos</Button>
      </ClearConfirmationDialog>
    </QueryClientProvider>
  );
}

describe('ClearConfirmationDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetClearable.mockResolvedValue({ data: downloads } as AxiosResponse);
  });

  it('renders trigger button', () => {
    renderDialog();
    expect(screen.getByText('Limpar todos')).toBeInTheDocument();
  });

  it('opens dialog and lists clearable downloads', async () => {
    renderDialog();
    fireEvent.click(screen.getByText('Limpar todos'));

    expect(screen.getByText('Limpar downloads')).toBeInTheDocument();
    expect(screen.getByText(/2 downloads prontos para limpar/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Movie One')).toBeInTheDocument());
    expect(screen.getByText('Movie Two')).toBeInTheDocument();
  });

  it('calls onClear with all items and delete_files=false when none checked', async () => {
    const onClear = vi.fn();
    renderDialog({ onClear });
    fireEvent.click(screen.getByText('Limpar todos'));
    await waitFor(() => expect(screen.getByText('Movie One')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Limpar 2 downloads' }));

    expect(onClear).toHaveBeenCalledWith([
      { id: 1, delete_files: false },
      { id: 2, delete_files: false },
    ]);
  });

  it('includes delete_files=true for checked downloads', async () => {
    const onClear = vi.fn();
    renderDialog({ onClear });
    fireEvent.click(screen.getByText('Limpar todos'));
    await waitFor(() => expect(screen.getByText('Movie One')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('checkbox', { name: /Movie One/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Limpar e deletar 2 downloads' }));

    expect(onClear).toHaveBeenCalledWith([
      { id: 1, delete_files: true },
      { id: 2, delete_files: false },
    ]);
  });

  it('uses singular form when clearableCount is 1', () => {
    renderDialog({ clearableCount: 1 });
    fireEvent.click(screen.getByText('Limpar todos'));
    expect(screen.getByText(/1 download pronto para limpar/)).toBeInTheDocument();
  });
});
