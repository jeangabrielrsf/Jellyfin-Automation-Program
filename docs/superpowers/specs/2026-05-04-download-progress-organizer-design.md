# Design: Download Progress Monitor + Smart Save Paths

## Date: 2026-05-04

## Context

A aplicação Jellyfin Automation conecta busca (TMDB/Jackett) com download (qBittorrent). O download de torrents agora funciona corretamente, mas faltam duas features críticas:

1. **Progresso não é monitorado** - A barra de progresso no frontend mostra 0% e não atualiza durante o download. O status também não muda para "Concluído" quando termina.
2. **Pasta de salvamento não é inteligente** - Torrents são baixados na pasta padrão do qBittorrent (Downloads). O ideal é salvar diretamente na estrutura organizada: `Series/Nome da Série/Season XX/`.

## Goals

1. Monitorar progresso de downloads ativos no qBittorrent e atualizar o banco de dados
2. Atualizar status para COMPLETED quando o download terminar
3. Definir savepath correto ao adicionar torrent ao qBittorrent
4. Organizar automaticamente arquivos quando download completa

## Architecture

### Download Progress Worker

Um worker async que roda no `lifespan` do FastAPI:

```python
class DownloadWorker:
    """Background worker to monitor qBittorrent downloads."""
    
    INTERVAL = 10  # seconds
    
    async def start(self):
        while True:
            await self._sync_progress()
            await asyncio.sleep(self.INTERVAL)
    
    async def _sync_progress(self):
        # 1. Query DB for DOWNLOADING downloads
        # 2. Get all torrents from qBittorrent
        # 3. Match by torrent_hash
        # 4. Update DB (progress, speed, eta, status)
        # 5. If completed, trigger organization
```

**States mapping (qBittorrent → app):**
- `downloading` → `DOWNLOADING`
- `stalledDL` (stalled download) → `DOWNLOADING` (still downloading but no peers)
- `pausedDL` → `PAUSED`
- `queuedDL` / `checkingDL` → `PENDING`
- `uploading` / `stalledUP` → `COMPLETED` (if progress == 1.0)

**Data Flow:**
```
FastAPI Lifespan
  └── DownloadWorker.start()
        └── every 10s:
              ├── query DB: status == DOWNLOADING
              ├── qbittorrent.get_torrents()
              ├── match by torrent_hash
              ├── update DB: progress, speed, eta, status
              ├── if completed → status = COMPLETED
              └── trigger organize_files()
```

### Smart Save Paths

**Path Resolution Logic:**

Ao criar um download (`POST /api/downloads/`):

1. **Extrair temporada/episódio do nome do torrent:**
   - Regex: `S(\d{1,2})E(\d{1,2})` ou `(\d{1,2})x(\d{1,2})`
   - Ex: `The Rookie S08E17 1080p x265 ELiTE` → Season 8, Episode 17

2. **Calcular savepath baseado no tipo:**
   - **Movie:** `{MOVIES_PATH}/{Title} ({Year})/`
   - **Series:** `{SERIES_PATH}/{Title}/Season {season:02d}/`
   - **Anime:** `{ANIMES_PATH}/{Title}/Season {season:02d}/`

3. **Criar diretórios se não existirem:**
   - Os diretórios são montados no container via volumes no docker-compose
   - O backend precisa ter permissão de escrita

4. **Passar savepath para qBittorrent API:**
   - O campo `savepath` na chamada `/api/v2/torrents/add`

**Pós-download:**
- Quando o worker detecta que o download completou, chama o OrganizerService
- O OrganizerService move os arquivos da pasta de download para a pasta correta
- Renomeia os arquivos com o padrão: `{Title} - S{season:02d}E{episode:02d} - {quality}.{ext}`

## Components

| Component | File | Responsabilidade |
|-----------|------|------------------|
| `DownloadWorker` | `app/services/download_worker.py` | Loop principal, sync com qBittorrent |
| `PathResolver` | `app/services/path_resolver.py` | Calcula savepath baseado em tipo e metadados |
| `TorrentMatcher` | `app/services/qbittorrent_service.py` | Match por hash, extrai progresso/speed/eta |
| `OrganizerService` | `app/services/organizer_service.py` | Já existe - move/renomeia arquivos |

## API Changes

### `POST /api/downloads/`

Adicionar campo opcional `season` e `episode` no body:
```json
{
  "tmdb_id": 123,
  "title": "The Rookie",
  "media_type": "series",
  "torrent_name": "The Rookie S08E17 1080p x265 ELiTE",
  "magnet_link": "magnet:?xt=urn:btih:...",
  "quality": "1080p",
  "season": 8,
  "episode": 17
}
```

Se `season`/`episode` não forem fornecidos, extrair do `torrent_name`.

### `GET /api/downloads/`

Já retorna `progress`, `speed`, `eta` - o worker atualiza esses campos no DB.

## Data Model Changes

Nenhuma mudança necessária no modelo `Download` - já tem os campos:
- `progress` (Float)
- `speed` (String)
- `eta` (String)
- `status` (Enum)
- `torrent_hash` (String)
- `source_folder` (Text)
- `destination_folder` (Text)

## Error Handling

1. **qBittorrent não responde:** Worker continua rodando, tenta novamente no próximo ciclo
2. **Torrent não encontrado no qBittorrent:** Pode ter sido removido manualmente - marcar como FAILED
3. **Sem permissão para criar pasta:** Logar erro, marcar como FAILED
4. **Falha na organização:** Marcar como COMPLETED mas logar erro de organização

## Testing Strategy

1. **Teste do Worker:** Mock qBittorrent API, verificar que o DB é atualizado corretamente
2. **Teste do PathResolver:** Verificar extração de season/episode e criação de paths
3. **Teste de integração:** Criar download, verificar que savepath é correto

## Implementation Order

1. Implementar `PathResolver` e passar savepath para qBittorrent
2. Implementar `DownloadWorker` com sync de progresso
3. Integrar com OrganizerService quando completa
4. Testar fluxo completo: busca → download → progresso → organização
