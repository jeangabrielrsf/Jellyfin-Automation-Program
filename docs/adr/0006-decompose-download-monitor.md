# ADR 0006: Decompor DownloadMonitor em módulos focados

## Status

Aceito

## Contexto

O `DownloadMonitor.tsx` (454 linhas) mistura três concerns em um único módulo:

- **3 dialogs**: Clear confirmation (linhas 178-215), Cancel confirmation (217-260), Detail (262-451)
- **Lista de downloads** (linhas 77-176) — renderiza cards com status, progresso, ações
- **`statusConfig`** (linhas 22-30) — configuração de domínio (mapeia status → ícone/cor/label)
- **6 useState**: `selectedDownload`, `clearDialogOpen`, `cancelDialogOpen`, `downloadToCancel`, `deleteFilesOnClear`, `deleteFilesOnCancel`

Isso viola locality — a lógica de cada dialog está espalhada em um componente gigante, dificultando testes e reuso.

## Decisão

Extrair 5 módulos para `frontend/src/components/downloads/`:

### 1. `ClearConfirmationDialog`

Encapsula:
- State: `isOpen`, `deleteFiles`
- Props: `clearableCount`, `onConfirm(deleteFiles: boolean)`
- Lógica: reset state quando fecha

### 2. `CancelConfirmationDialog`

Encapsula:
- State: `isOpen`, `deleteFiles`
- Props: `download: Download | null`, `onConfirm(id: number, deleteFiles: boolean)`
- Lógica: reset state quando fecha

### 3. `DownloadDetailDialog`

Encapsula:
- Props: `download: Download | null`, `onClose()`
- Sem state interno (só renderiza o download selecionado)

### 4. `DownloadList`

Encapsula:
- Props: `downloads: Download[]`, `onPause`, `onResume`, `onCancel`, `onSelect`
- Renderiza cards com status, progresso, ações
- Usa `downloadStatusConfig`

### 5. `downloadStatusConfig`

Move `statusConfig` (linhas 22-30) para módulo separado:
```typescript
export const downloadStatusConfig: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  downloading: { icon: Download, color: 'text-sky-400', bg: 'bg-sky-400/10', label: 'Baixando' },
  // ...
};
```

### DownloadMonitor (composition root)

Fica com ~50 linhas:
- State: `selectedDownload`, `downloadToCancel`
- Callbacks: `onPause`, `onResume`, `onCancel`, `onClear` (recebidos via props)
- Composition: renderiza `DownloadList` + 3 dialogs

```tsx
export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
  onClear,
}) => {
  const [selectedDownload, setSelectedDownload] = useState<Download | null>(null);
  const [downloadToCancel, setDownloadToCancel] = useState<Download | null>(null);

  const clearableCount = downloads.filter(
    (d) => d.status !== 'pending' && d.status !== 'downloading'
  ).length;

  if (downloads.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-4">
      {clearableCount > 0 && (
        <div className="flex justify-end">
          <Button onClick={() => setClearDialogOpen(true)}>
            Limpar todos ({clearableCount})
          </Button>
        </div>
      )}
      
      <DownloadList
        downloads={downloads}
        onPause={onPause}
        onResume={onResume}
        onCancel={(download) => {
          setDownloadToCancel(download);
          setCancelDialogOpen(true);
        }}
        onSelect={setSelectedDownload}
      />

      <ClearConfirmationDialog
        clearableCount={clearableCount}
        onConfirm={onClear}
      />

      <CancelConfirmationDialog
        download={downloadToCancel}
        onConfirm={onCancel}
      />

      <DownloadDetailDialog
        download={selectedDownload}
        onClose={() => setSelectedDownload(null)}
      />
    </div>
  );
};
```

## Consequências

### Positivas

- **Locality:** cada dialog concentra em um módulo, testável isoladamente
- **Leverage:** `DownloadList` reutilizável em outras páginas (ex: Search, Detail)
- **Testabilidade:** dialogs testáveis sem renderizar a lista inteira
- **Interface shrinks:** DownloadMonitor cai de 454 para ~50 linhas

### Negativas

- 5 novos arquivos para manter
- `components/downloads/` adiciona uma camada de indireção

### Riscos

- Se o `DownloadDetailDialog` crescer muito (ex: adicionar abas, gráficos), pode precisar ser decomposto novamente
- `downloadStatusConfig` pode precisar de mais campos no futuro (ex: tooltip, description)

## Alternativas Consideradas

**Alternativa 1: State no DownloadMonitor (status quo)**

Manter todos os states no DownloadMonitor e passar via props para cada dialog.

Rejeitada: DownloadMonitor continua com 6 useState e lógica de reset. Cada dialog não é self-contained.

**Alternativa 2: Context API**

Criar `DownloadMonitorContext` para compartilhar state entre todos os componentes.

Rejeitada: overkill para 4 componentes. Context é útil quando muitos componentes precisam do mesmo state — aqui cada dialog é independente.

**Alternativa 3: Feature-based (`features/downloads/components/`)**

Agrupar por domínio em estrutura feature-based.

Rejeitada: não existe estrutura feature-based no projeto. `components/downloads/` é mais leve e pode migrar no futuro se necessário.

**Alternativa 4: Não extrair `downloadStatusConfig`**

Manter `statusConfig` no DownloadMonitor e passar via props para `DownloadList`.

Rejeitada: `statusConfig` é conhecimento de domínio (mapeia status → UI), não do composition root. Mover para módulo separado permite reuso e teste isolado.

## Implementação

Arquivos a criar/modificar:

- `frontend/src/components/downloads/ClearConfirmationDialog.tsx` (novo)
- `frontend/src/components/downloads/CancelConfirmationDialog.tsx` (novo)
- `frontend/src/components/downloads/DownloadDetailDialog.tsx` (novo)
- `frontend/src/components/downloads/DownloadList.tsx` (novo)
- `frontend/src/components/downloads/downloadStatusConfig.ts` (novo)
- `frontend/src/components/DownloadMonitor.tsx` — reduzir para ~50 linhas (composition root)
