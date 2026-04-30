# Especificação de Design — Jellyfin Automation

**Data:** 2025-04-30  
**Versão:** 1.0  
**Status:** Implementado

---

## 1. Visão Geral

O Jellyfin Automation é uma aplicação full-stack para automatizar o fluxo completo de aquisição e organização de conteúdo de mídia (filmes, séries, animes), integrando-se com Jellyfin como media server.

### 1.1 Objetivos
- Reduzir intervenção manual no processo de download e organização
- Fornecer interface web intuitiva para busca e gerenciamento
- Garantir rastreabilidade via logs estruturados
- Suportar deploy simplificado via Docker

### 1.2 Escopo
- Busca de metadados via TMDB
- Busca de torrents via Jackett
- Gerenciamento de downloads via qBittorrent Web API
- Organização automática de arquivos em estrutura de biblioteca
- Notificação de atualização de biblioteca ao Jellyfin
- Monitoramento em tempo real via WebSocket

---

## 2. Arquitetura de Sistema

### 2.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        Cliente                               │
│                   Navegador Web                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (opcional)                        │
│                   Proxy Reverso + Static                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐
│     Frontend        │   │      Backend        │
│   React + Vite      │   │   FastAPI + Uvicorn │
│   Porta: 3000       │   │   Porta: 8000       │
└─────────────────────┘   └─────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌─────────┐   ┌──────────┐   ┌──────────┐
              │PostgreSQL│   │qBittorrent│   │  Jellyfin │
              │  5432   │   │  8080    │   │  8096    │
              └─────────┘   └──────────┘   └──────────┘
                    │
                    ▼
              ┌──────────┐
              │  Jackett  │
              │  9117    │
              └──────────┘
```

### 2.2 Camadas do Backend

| Camada | Responsabilidade | Tecnologia |
|--------|------------------|------------|
| API/Router | Expor endpoints REST e WebSocket | FastAPI APIRouter |
| Service | Orquestrar lógica de negócio e integrações | Classes Python assíncronas |
| Scraper | Extrair dados de indexadores | JackettScraper (parser XML/JSON) |
| Model | Definir schema do banco de dados | SQLAlchemy ORM |
| Config | Carregar e validar variáveis de ambiente | Pydantic Settings |
| Logging | Estruturar e rotacionar logs | Loguru + Structlog |

### 2.3 Fluxo de Dados

#### 2.3.1 Busca e Download
1. Usuário busca "The Matrix" no frontend
2. Frontend → `GET /api/search/?q=The+Matrix`
3. Backend consulta TMDB API → retorna resultados
4. Usuário seleciona filme → Frontend → `GET /api/search/torrents?tmdb_id=603`
5. Backend consulta Jackett → retorna torrents ranqueados
6. Usuário clica em Download → Frontend → `POST /api/downloads`
7. Backend:
   - Cria registro no PostgreSQL (status: pending)
   - Adiciona torrent ao qBittorrent via API
   - Envia update via WebSocket

#### 2.3.2 Organização Automática
1. Monitor service (planejado) ou polling verifica downloads completos
2. Ao detectar conclusão:
   - Chama `OrganizerService` para mover/renomear arquivos
   - Atualiza status no banco para "organized"
   - Chama `JellyfinService.scan_library()` para atualizar biblioteca
   - Envia notificação via WebSocket

---

## 3. Modelagem de Dados

### 3.1 Entidades Principais

#### Download
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer (PK) | Identificador único |
| tmdb_id | Integer | ID do TMDB |
| title | String(255) | Título do conteúdo |
| type | Enum (movie/series/anime) | Tipo de conteúdo |
| torrent_name | String(500) | Nome do torrent |
| torrent_hash | String(64), unique | Hash do torrent no qBittorrent |
| magnet_link | Text | Link magnet |
| quality | String(20) | Qualidade (1080p, 720p, etc) |
| language_preference | String(50) | Idioma preferido |
| status | Enum | pending/downloading/completed/failed/cancelled/organized |
| progress | Float | Progresso 0-100 |
| speed | String(50) | Velocidade atual |
| eta | String(50) | Tempo estimado |
| source_folder | Text | Pasta de origem no qBittorrent |
| destination_folder | Text | Pasta final organizada |
| indexer_used | String(100) | Indexador Jackett utilizado |
| error_message | Text | Mensagem de erro, se houver |
| created_at | DateTime | Data de criação |
| updated_at | DateTime | Última atualização |
| completed_at | DateTime | Data de conclusão |

#### Settings
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer (PK) | Identificador |
| key | String(100), unique | Nome da configuração |
| value | JSON | Valor arbitrário |
| updated_at | DateTime | Última alteração |

### 3.2 Diagrama ER

```
┌─────────────┐       ┌─────────────┐
│  downloads  │       │  settings   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ tmdb_id     │       │ key (UQ)    │
│ title       │       │ value (JSON)│
│ type        │       │ updated_at  │
│ torrent_name│       └─────────────┘
│ torrent_hash│
│ magnet_link │
│ quality     │
│ language    │
│ status      │
│ progress    │
│ speed       │
│ eta         │
│ source      │
│ destination │
│ indexer     │
│ error       │
│ created_at  │
│ updated_at  │
│ completed_at│
└─────────────┘
```

---

## 4. API Design

### 4.1 REST Endpoints

#### Search
```
GET /api/search/?q={query}&page={page}
→ TMDBSearchResult[]

GET /api/search/movie/{id}
→ TMDBDetail

GET /api/search/tv/{id}
→ TMDBDetail

GET /api/search/torrents?tmdb_id={id}&title={title}&media_type={type}
→ TorrentResult[]
```

#### Downloads
```
GET /api/downloads?status={status}
→ Download[]

POST /api/downloads
Body: { tmdb_id, title, media_type, torrent_name, magnet_link, quality, language_preference, indexer_used }
→ Download

GET /api/downloads/{id}
→ Download

DELETE /api/downloads/{id}
→ { message: "Download cancelled" }

POST /api/downloads/{id}/pause
→ { message: "Download paused" }

POST /api/downloads/{id}/resume
→ { message: "Download resumed" }
```

#### Settings
```
GET /api/settings
→ { [key]: value }

PUT /api/settings/{key}
Body: any
→ { message: "Setting updated" }
```

#### Logs
```
GET /api/logs?level={level}&lines={lines}&search={search}
→ { logs: string[] }
```

### 4.2 WebSocket Protocol

**Endpoint:** `ws://host:8000/api/ws`

**Mensagens do Servidor:**
```json
{
  "type": "download_update",
  "data": {
    "id": 1,
    "status": "downloading",
    "progress": 45.5,
    "speed": "2.5 MB/s",
    "eta": "00:10:30"
  }
}
```

```json
{
  "type": "download_completed",
  "data": {
    "id": 1,
    "title": "The Matrix",
    "destination_folder": "/movies/The Matrix (1999)"
  }
}
```

---

## 5. Frontend Design

### 5.1 Estrutura de Componentes

```
src/
├── pages/
│   ├── Home.tsx          # Dashboard com estatísticas
│   ├── Search.tsx        # Busca TMDB + torrents
│   ├── Downloads.tsx     # Lista e monitoramento
│   ├── Settings.tsx      # Configurações da aplicação
│   └── Logs.tsx          # Visualizador de logs
├── components/
│   ├── SearchBar.tsx     # Input de busca com debounce
│   ├── MediaCard.tsx     # Card de filme/série
│   ├── TorrentList.tsx   # Lista de torrents
│   └── DownloadMonitor.tsx # Tabela de downloads com progresso
├── services/
│   └── api.ts            # Cliente Axios com endpoints
├── types/
│   └── index.ts          # Interfaces TypeScript
└── main.tsx              # Entry point com QueryClient
```

### 5.2 Estado e Data Fetching

- **TanStack Query** gerencia todo o estado server-side
- Polling automático de 5s na página de downloads (`refetchInterval: 5000`)
- Cache invalidado após mutações (pause/resume/cancel/create)
- Nenhum estado global client-side complexo necessário

### 5.3 Design System

- **TailwindCSS** para estilização utilitária
- Componentes base em `components/ui/` (Button, Input, Card, Badge, Progress, Select)
- Tema escuro por padrão
- Layout responsivo: mobile-first com grid adaptativo

---

## 6. Integrações Externas

### 6.1 TMDB API
- **Base URL:** `https://api.themoviedb.org/3`
- **Autenticação:** Query param `api_key`
- **Endpoints usados:**
  - `/search/multi` — Busca geral
  - `/movie/{id}` — Detalhes de filme
  - `/tv/{id}` — Detalhes de série
- **Cache:** Não implementado (recomendado para produção)

### 6.2 Jackett API
- **Base URL:** Configurável via `JACKETT_URL`
- **Autenticação:** Query param `apikey`
- **Endpoint:** `/api/v2.0/indexers/all/results`
- **Parâmetros:** `Query={title}`, `Category={category}`
- **Parsing:** XML → JSON com extração de seeds, peers, tamanho

### 6.3 qBittorrent Web API
- **Base URL:** Configurável via `QBITTORRENT_HOST`
- **Autenticação:** POST `/api/v2/auth/login`
- **Endpoints usados:**
  - `/api/v2/torrents/add` — Adicionar torrent
  - `/api/v2/torrents/info` — Listar torrents
  - `/api/v2/torrents/pause` — Pausar
  - `/api/v2/torrents/resume` — Continuar
  - `/api/v2/torrents/delete` — Remover
- **Gerenciamento de sessão:** Cookie de autenticação via httpx

### 6.4 Jellyfin API
- **Base URL:** Configurável via `JELLYFIN_URL`
- **Autenticação:** Header `X-Emby-Token`
- **Endpoints usados:**
  - `/Library/Refresh` — Atualizar bibliotecas
  - `/Library/VirtualFolders` — Listar bibliotecas

---

## 7. Serviços Internos

### 7.1 OrganizerService
- **Responsabilidade:** Mover e renomear arquivos de download para estrutura de biblioteca
- **Métodos:**
  - `organize_movie(source, title, year, quality)` → `/movies/{title} ({year})/{title} ({year}) - {quality}.ext`
  - `organize_series(source, title, season, episode, quality)` → `/series/{title}/Season {NN}/{title} - S{NN}E{NN} - {quality}.ext`
  - `organize_anime(source, title, season, episode, quality)` → `/animes/{title}/Season {NN}/{title} - S{NN}E{NN} - {quality}.ext`
- **Regras:**
  - Identifica maior arquivo de vídeo como principal
  - Move legendas (.srt, .ass) com nome correspondente
  - Remove arquivos desnecessários (.nfo, sample, .txt, imagens)
  - Limpa diretórios vazios após organização

### 7.2 Monitor Service (planejado)
- **Responsabilidade:** Polling periódico do qBittorrent para detectar downloads completos
- **Ações ao detectar conclusão:**
  1. Chamar OrganizerService
  2. Atualizar status no banco
  3. Chamar JellyfinService.scan_library()
  4. Notificar via WebSocket
- **Frequência:** A cada 30-60 segundos (configurável)

---

## 8. Segurança

### 8.1 Autenticação
- JWT tokens para autenticação de usuários (preparado no backend, não implementado no frontend)
- API Keys para serviços externos (TMDB, Jackett, Jellyfin)
- Credenciais do qBittorrent nunca expostas ao cliente

### 8.2 Validação
- Pydantic models validam todos os inputs da API
- SQLAlchemy ORM previne SQL injection
- httpx timeout evita requests bloqueantes indefinidamente

### 8.3 Configuração Sensível
- `.env` e `.env.example` documentam todas as variáveis
- `SECRET_KEY` deve ser alterada em produção
- Logs não registram senhas ou API keys

---

## 9. Deploy

### 9.1 Docker Compose

O `docker-compose.yml` orquestra 3 serviços:
- **db**: PostgreSQL 15 Alpine com healthcheck
- **backend**: FastAPI com build automático e migrações na inicialização
- **frontend**: Nginx servindo build estático do React com proxy para `/api`

### 9.2 Volumes
- `postgres_data`: Persistência do banco
- `./media/*`: Pastas de mídia montadas do host
- `./backend/logs`: Logs persistentes do backend

### 9.3 Variáveis de Ambiente Obrigatórias para Produção
- `DATABASE_URL`
- `TMDB_API_KEY`
- `JACKETT_URL` + `JACKETT_API_KEY`
- `QBITTORRENT_HOST` + credenciais
- `JELLYFIN_URL` + `JELLYFIN_API_KEY`
- `SECRET_KEY`
- `MOVIES_PATH`, `SERIES_PATH`, `ANIMES_PATH`

---

## 10. Testes

### 10.1 Estratégia
- **Unit tests** para todos os services e configurações
- **Integration tests** para routers com SQLite in-memory
- **Frontend build test** para validar TypeScript e bundle

### 10.2 Fixtures Compartilhadas
- `conftest.py`:
  - Engine SQLite in-memory com `StaticPool`
  - Override de `get_db` dependency
  - Mock de lifespan para evitar conexões PostgreSQL

### 10.3 Cobertura
| Módulo | Test File | Status |
|--------|-----------|--------|
| Config | `test_config.py` | 3 passando |
| Logging | `test_logging.py` | 2 passando |
| TMDB Service | `test_tmdb_service.py` | 7 passando |
| Scrapers | `test_scrapers.py` | 2 passando |
| qBittorrent Service | `test_qbittorrent_service.py` | 3 passando |
| Organizer Service | `test_organizer_service.py` | 6 passando |
| Jellyfin Service | `test_jellyfin_service.py` | 4 passando |
| Routers + WebSocket | `test_routers.py` | 18 passando |
| **Total** | | **45 passando** |

---

## 11. Logs e Observabilidade

### 11.1 Logging Estruturado
- **Loguru** para saída formatada em arquivo e console
- **Structlog** para contexto rico (key-value pairs)
- Rotação automática: 10MB por arquivo, máximo 5 arquivos
- Formato JSON opcional para ingestão em ELK/Loki

### 11.2 Endpoints de Debug
- `GET /api/logs` — Retorna últimas N linhas do log
- Filtros por nível (DEBUG, INFO, WARNING, ERROR)
- Busca por texto com regex

---

## 12. Decisões Técnicas

### 12.1 SQLAlchemy 2.0 vs 1.4
- Escolhido 2.0 por melhor suporte a type hints e API mais consistente
- Aviso de deprecatação em `declarative_base()` corrigido para usar `sqlalchemy.orm.declarative_base()`

### 12.2 Pydantic V2
- Models de request/response usam Pydantic V2
- Settings via `pydantic-settings` com suporte a `.env`
- `orm_mode` substituído por `from_attributes` no V2

### 12.3 PostgreSQL vs SQLite
- **Desenvolvimento:** SQLite in-memory para testes
- **Produção:** PostgreSQL via Docker Compose
- Migrações via Alembic garantem compatibilidade entre ambientes

### 12.4 React + Vite vs Next.js
- Escolhido Vite por simplicidade e build mais rápido
- SPA (Single Page Application) é suficiente para o escopo
- Não há necessidade de SSR ou rotas dinâmicas no servidor

---

## 13. Roadmap Futuro

- [ ] **Autenticação de usuários** — JWT + login screen
- [ ] **Monitor Service** — Background task para detectar downloads completos
- [ ] **Notificações** — Push notifications ou webhook para downloads completos
- [ ] **Cache TMDB** — Redis para cachear resultados de busca
- [ ] **Filtros avançados** — Por codec, release group, dublado/legendado
- [ ] **Agendamento** — Busca automática por novos episódios de séries
- [ ] **Dashboard** — Estatísticas de uso e histórico

---

## 14. Referências

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TanStack Query](https://tanstack.com/query/latest)
- [TailwindCSS](https://tailwindcss.com/)
- [TMDB API](https://developer.themoviedb.org/docs)
- [qBittorrent Web API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1))
- [Jackett API](https://github.com/Jackett/Jackett)
- [Jellyfin API](https://api.jellyfin.org/)
