import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CancelConfirmationDialog } from './CancelConfirmationDialog';
import type { Download } from '@/types';

describe('CancelConfirmationDialog', () => {
  const mockDownload: Download = {
    id: 1,
    tmdb_id: 123,
    title: 'Test Movie',
    type: 'movie',
    quality: '1080p',
    language_preference: 'Legendado',
    status: 'downloading',
    progress: 0.5,
    created_at: '2024-01-15T10:00:00Z',
  };

  const defaultProps = {
    download: mockDownload,
    onCancel: vi.fn(),
  };

  it('renders nothing when closed', () => {
    render(<CancelConfirmationDialog {...defaultProps} />);
    expect(screen.queryByText('Cancelar download')).not.toBeInTheDocument();
  });

  it('renders dialog content when open', () => {
    render(<CancelConfirmationDialog {...defaultProps} isOpen={true} />);
    expect(screen.getByRole('heading', { name: 'Cancelar download' })).toBeInTheDocument();
    expect(screen.getByText(/Tem certeza que deseja cancelar o download de/)).toBeInTheDocument();
    expect(screen.getByText(/Test Movie/)).toBeInTheDocument();
  });

  it('calls onCancel with deleteFiles=false when confirm clicked without checkbox', () => {
    render(<CancelConfirmationDialog {...defaultProps} isOpen={true} />);
    
    const confirmButton = screen.getByRole('button', { name: 'Cancelar download' });
    fireEvent.click(confirmButton);
    
    expect(defaultProps.onCancel).toHaveBeenCalledWith(1, false);
  });

  it('calls onCancel with deleteFiles=true when checkbox is checked', () => {
    render(<CancelConfirmationDialog {...defaultProps} isOpen={true} />);
    
    const checkbox = screen.getByLabelText('Deletar arquivos parciais do disco');
    fireEvent.click(checkbox);
    
    const confirmButton = screen.getByRole('button', { name: 'Cancelar download' });
    fireEvent.click(confirmButton);
    
    expect(defaultProps.onCancel).toHaveBeenCalledWith(1, true);
  });

  it('resets deleteFiles state when dialog closes', () => {
    const { rerender } = render(<CancelConfirmationDialog {...defaultProps} isOpen={true} />);
    
    const checkbox = screen.getByLabelText('Deletar arquivos parciais do disco');
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
    
    rerender(<CancelConfirmationDialog {...defaultProps} isOpen={false} />);
    
    rerender(<CancelConfirmationDialog {...defaultProps} isOpen={true} />);
    const newCheckbox = screen.getByLabelText('Deletar arquivos parciais do disco');
    expect(newCheckbox).not.toBeChecked();
  });

  it('calls onClose when cancel button clicked', () => {
    const onClose = vi.fn();
    render(<CancelConfirmationDialog {...defaultProps} isOpen={true} onClose={onClose} />);
    
    const backButton = screen.getByRole('button', { name: 'Voltar' });
    fireEvent.click(backButton);
    
    expect(onClose).toHaveBeenCalled();
  });
});
