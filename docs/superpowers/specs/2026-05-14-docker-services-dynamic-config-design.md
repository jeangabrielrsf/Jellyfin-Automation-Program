# Design Spec: Docker Services + Dynamic Configuration

**Date:** 2026-05-14
**Author:** opencode
**Status:** Draft — awaiting review

## Problem

1. Jackett e qBittorrent rodam manualmente no Windows, tornando a instalação mais complexa e dependente de configuração externa.
2. Chaves de API e URLs de serviços (TMDB, OMDB, Jackett, qBittorrent, Jellyfin) são configuráveis apenas via `.env`, exigindo edição manual de arquivo antes do primeiro uso.

## Solution Overview

### Parte 1: Dockerizar qBittorrent e Jackett

Adicionar ambos ao `docker-compose.yml` com persistência via volumes. Backend conecta via Docker network interna.

### Parte 2: Configuração dinâmica via UI

Criar um `ConfigService` unificado que lê configurações com prioridade: **DB > .env > erro**. Refatorar todos os services para usar este padrão. Adicionar seção "Serviços Externos" na Settings page.

---

## Architecture

### ConfigService — Priority Chain

```
get_config(key, db, required=True)
  │
  ├─ 1. DB query (Setting table)
  │   └─ found? → return value
  │
  ├─ 2. .env fallback (get_settings())
  │   └─ found and non-empty? → return value
  │
  └─ 3. required=True? → raise ConfigurationError
       required=False? → return ""
```

**`ConfigurationError`** — exceção customizada (`app/exceptions.py`). Quando lançada dentro de um router, é capturada por um middleware que retorna HTTP 500 com JSON: `{"error": "Missing required config: '<key>'. Set it via UI or .env"}`.

### Service Refactoring Pattern

Cada service aceita `db: Session | None = None` no `__init__`:

```python
class TMDBService:
    def __init__(self, db: Session | None = None):
        self.db = db
        self.api_key = get_config("tmdb_api_key", db, required=True)
```

Services afetados:
- `TMDBService` — `tmdb_api_key`
- `DiscoverService` — `tmdb_api_key`
- `QBittorrentService` — `qbittorrent_host`, `qbittorrent_username`, `qbittorrent_password`
- `JackettScraper` — `jackett_url`, `jackett_api_key`, `jackett_timeout`
- `JellyfinService` — `jellyfin_url`, `jellyfin_api_key`
- `search.py` router (OMDB) — `omdb_api_key`
- `OrganizerService` — já suporta DB, adaptar para usar `get_config()`
- `PathResolver` — já suporta DB, adaptar para usar `get_config()`

### Router Changes

Routers já recebem `db` via `Depends(get_db)`. Basta passar `db` ao instanciar services:

```python
@router.get("/...")
def some_endpoint(db: Session = Depends(get_db)):
    tmdb = TMDBService(db=db)
    ...
```

### DownloadWorker

Já cria instâncias fresh a cada ciclo de 10s. Precisa obter `db` session internamente (cria sua própria session por ciclo) e passar aos services.

---

## Docker Compose Changes

### qBittorrent

```yaml
qbittorrent:
  image: lscr.io/linuxserver/qbittorrent:latest
  restart: always
  environment:
    - PUID=1000
    - PGID=1000
    - WEBUI_PORT=8080
    - TZ=America/Sao_Paulo
  volumes:
    - ./qbittorrent/config:/config
    - ${TORRENTS_PATH:-/mnt/d/Torrents}:/downloads
  ports:
    - "8080:8080"
    - "6881:6881"
    - "6881:6881/udp"
```

### Jackett

```yaml
jackett:
  image: lscr.io/linuxserver/jackett:latest
  restart: always
  environment:
    - PUID=1000
    - PGID=1000
    - TZ=America/Sao_Paulo
  volumes:
    - ./jackett/config:/config
    - ${TORRENTS_PATH:-/mnt/d/Torrents}:/downloads
  ports:
    - "9117:9117"
```

### Backend Changes

- Remove `network_mode: "host"` — usa Docker network padrão
- Defaults de `.env` para serviços internos mudam de `localhost` para nomes de serviço:
  - `JACKETT_URL=http://jackett:9117`
  - `QBITTORRENT_HOST=http://qbittorrent:8080`
- Adicionar `depends_on: [qbittorrent, jackett]` com health checks opcionais
- Manter volumes `/mnt:/mnt` para acesso aos paths de biblioteca

### Frontend

- Adicionar `extra_hosts` ou usar Docker network para proxy (já configurado no compose atual)

---

## Settings Page — Nova Seção "Serviços Externos"

Novo grupo na UI abaixo dos existentes (Caminhos, Preferências):

| Campo | Key no DB | Tipo | Máscara |
|-------|-----------|------|---------|
| TMDB API Key | `tmdb_api_key` | text | Sim (****) |
| OMDB API Key | `omdb_api_key` | text | Sim (****) |
| Jackett URL | `jackett_url` | text | Não |
| Jackett API Key | `jackett_api_key` | text | Sim (****) |
| qBittorrent Host | `qbittorrent_host` | text | Não |
| qBittorrent Username | `qbittorrent_username` | text | Não |
| qBittorrent Password | `qbittorrent_password` | password | Sim (****) |
| Jellyfin URL | `jellyfin_url` | text | Não |
| Jellyfin API Key | `jellyfin_api_key` | text | Sim (****) |

**Comportamento:**
- Campos mostram valor atual do DB. Se não existir no DB, mostra placeholder indicando valor do `.env`
- Botão "Salvar" por campo (mesmo pattern atual)
- Valores sensíveis (API keys, senhas) são mascarados com `****` por padrão; botão "mostrar" revela
- Validação: campos URL devem ser URLs válidas; campos obrigatórios não podem ser vazios

### Teste de Conexão (opcional, fase 2)

Botão "Testar" ao lado de cada serviço que faz uma chamada de teste:
- TMDB: `GET /search/movie?query=test&api_key={key}`
- Jackett: `GET /api/v2.0/indexers/all/results/torznab?apikey={key}`
- qBittorrent: `POST /api/v2/auth/login`
- Jellyfin: `GET /System/Info/Public` com header `X-Emby-Token`

---

## Seed Inicial

Na inicialização do backend (lifespan), verificar se as configs críticas existem no DB. Se não existirem mas existirem no `.env`, popular o DB:

```python
def seed_defaults_from_env(db: Session):
    """Populate DB with .env values if DB keys are missing."""
    env = get_settings()
    critical_keys = [
        "tmdb_api_key", "omdb_api_key",
        "jackett_url", "jackett_api_key",
        "qbittorrent_host", "qbittorrent_username", "qbittorrent_password",
        "jellyfin_url", "jellyfin_api_key",
        "movies_path", "series_path", "animes_path",
    ]
    for key in critical_keys:
        existing = db.query(Setting).filter(Setting.key == key).first()
        if not existing:
            env_value = getattr(env, key, None)
            if env_value:
                db.add(Setting(key=key, value=env_value))
    db.commit()
```

Isso garante transição suave: quem já tem `.env` configurado não precisa reconfigurar pela UI.

---

## Error Handling

### ConfigurationError

```python
class ConfigurationError(Exception):
    def __init__(self, key: str, message: str | None = None):
        self.key = key
        self.message = message or f"Missing required config: '{key}'. Set it via UI or .env"
        super().__init__(self.message)
```

### HTTP Error Handler

Middleware ou exception handler no FastAPI captura `ConfigurationError` e retorna:

```json
{
  "error": "configuration_error",
  "key": "tmdb_api_key",
  "message": "Missing required config: 'tmdb_api_key'. Set it via UI or .env"
}
```

Status: **500** (serviço indisponível por falta de configuração).

### Frontend Error Handling

Se a API retornar `configuration_error`, a UI pode:
- Mostrar toast: "Configuração ausente: TMDB API Key. Vá para Configurações para definir."
- Link direto para `/settings`

---

## Migration

Não requer migration de schema — o modelo `Setting` (key-value JSON) já suporta qualquer configuração.

O seed inicial roda no lifespan do app, antes do `DownloadWorker` iniciar.

---

## Testing

### Backend
- Testar `get_config()` com: (a) valor no DB, (b) valor apenas no `.env`, (c) nenhum dos dois → erro
- Testar cada service com `db=None` (fallback `.env`) e `db=session` (DB priority)
- Testar seed inicial com `.env` populado e DB vazio

### Frontend
- Testar renderização da nova seção "Serviços Externos"
- Testar save de cada campo
- Testar máscara de valores sensíveis (show/hide toggle)

---

## Files Changed

### New
- `backend/app/exceptions.py` — `ConfigurationError`
- `backend/app/services/config_service.py` — `get_config()`

### Modified
- `docker-compose.yml` — adicionar qBittorrent, Jackett; ajustar backend
- `backend/app/services/tmdb_service.py` — usar `get_config()`
- `backend/app/services/discover_service.py` — usar `get_config()`
- `backend/app/services/qbittorrent_service.py` — usar `get_config()`
- `backend/app/scrapers/jackett_scraper.py` — usar `get_config()`
- `backend/app/services/jellyfin_service.py` — usar `get_config()`
- `backend/app/services/organizer_service.py` — usar `get_config()`
- `backend/app/services/path_resolver.py` — usar `get_config()`
- `backend/app/services/download_worker.py` — passar `db` aos services
- `backend/app/routers/search.py` — passar `db` aos services (OMDB)
- `backend/app/routers/settings.py` — remover validação específica de path (generalizar)
- `backend/app/main.py` — adicionar seed inicial no lifespan
- `frontend/src/pages/Settings.tsx` — adicionar seção "Serviços Externos"
- `frontend/src/services/api.ts` — adicionar `settingsAPI.testConnection()` (se fase 2)
- `.env.example` — atualizar defaults para Docker network
