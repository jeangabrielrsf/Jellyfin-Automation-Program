import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ClearConfirmationDialog } from './ClearConfirmationDialog';
import { Button } from '@/components/ui/button';

describe('ClearConfirmationDialog', () => {
  const defaultProps = {
    clearableCount: 5,
    onClear: vi.fn(),
  };

  it('renders trigger button', () => {
    render(
      <ClearConfirmationDialog {...defaultProps}>
        <Button>Limpar todos</Button>
      </ClearConfirmationDialog>
    );
    expect(screen.getByText('Limpar todos')).toBeInTheDocument();
  });

  it('opens dialog when trigger clicked', () => {
    render(
      <ClearConfirmationDialog {...defaultProps}>
        <Button>Limpar todos</Button>
      </ClearConfirmationDialog>
    );
    
    const trigger = screen.getByText('Limpar todos');
    fireEvent.click(trigger);
    
    expect(screen.getByText('Limpar downloads')).toBeInTheDocument();
    expect(screen.getByText(/Isso removerá 5 downloads/)).toBeInTheDocument();
  });

  it('calls onClear with deleteFiles=false when confirm clicked without checkbox', () => {
    render(
      <ClearConfirmationDialog {...defaultProps}>
        <Button>Limpar todos</Button>
      </ClearConfirmationDialog>
    );
    
    const trigger = screen.getByText('Limpar todos');
    fireEvent.click(trigger);
    
    const confirmButton = screen.getByRole('button', { name: 'Limpar 5 downloads' });
    fireEvent.click(confirmButton);
    
    expect(defaultProps.onClear).toHaveBeenCalledWith(false);
  });

  it('calls onClear with deleteFiles=true when checkbox is checked', () => {
    render(
      <ClearConfirmationDialog {...defaultProps}>
        <Button>Limpar todos</Button>
      </ClearConfirmationDialog>
    );
    
    const trigger = screen.getByText('Limpar todos');
    fireEvent.click(trigger);
    
    const checkbox = screen.getByLabelText('Deletar arquivos baixados do disco');
    fireEvent.click(checkbox);
    
    const confirmButton = screen.getByRole('button', { name: 'Limpar 5 downloads' });
    fireEvent.click(confirmButton);
    
    expect(defaultProps.onClear).toHaveBeenCalledWith(true);
  });

  it('resets deleteFiles state when dialog closes', () => {
    render(
      <ClearConfirmationDialog {...defaultProps}>
        <Button>Limpar todos</Button>
      </ClearConfirmationDialog>
    );
    
    const trigger = screen.getByText('Limpar todos');
    fireEvent.click(trigger);
    
    const checkbox = screen.getByLabelText('Deletar arquivos baixados do disco');
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
    
    const cancelButton = screen.getByRole('button', { name: 'Cancelar' });
    fireEvent.click(cancelButton);
    
    fireEvent.click(trigger);
    const newCheckbox = screen.getByLabelText('Deletar arquivos baixados do disco');
    expect(newCheckbox).not.toBeChecked();
  });

  it('shows singular form when clearableCount is 1', () => {
    render(
      <ClearConfirmationDialog {...defaultProps} clearableCount={1}>
        <Button>Limpar</Button>
      </ClearConfirmationDialog>
    );
    
    const trigger = screen.getByText('Limpar');
    fireEvent.click(trigger);
    
    expect(screen.getByText(/Isso removerá 1 download concluído/)).toBeInTheDocument();
  });
});
