# Jellyfin Automation

Aplicação full-stack para automação de downloads de filmes, séries e animes, com organização automática de bibliotecas e integração com Jellyfin.

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação via Docker (Recomendado)](#instalação-via-docker-recomendado)
- [Configuração Pós-Instalação](#configuração-pós-instalação)
- [Instalação Manual (Desenvolvimento)](#instalação-manual-desenvolvimento)
- [Uso](#uso)
- [Testes](#testes)
- [API](#api)
- [WebSocket](#websocket)
- [Contribuição](#contribuição)

---

## Visão Geral

O **Jellyfin Automation** permite:

1. **Buscar conteúdo** na API do TMDB (The Movie Database)
2. **Encontrar torrents** via indexadores Jackett
3. **Adicionar downloads** ao qBittorrent automaticamente
4. **Monitorar progresso** de downloads em tempo real
5. **Organizar arquivos** automaticamente em pastas estruturadas
6. **Notificar o Jellyfin** para atualizar a biblioteca após conclusão

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│              (React + Vite + TailwindCSS)                   │
│                     Porta: 3001                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                        Caddy                                 │
│                  (Reverse Proxy)                             │
│                     Porta: 80                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│            (FastAPI + SQLAlchemy + Uvicorn)                 │
│                     Porta: 8000                              │
└──┬──────────────┬──────────────────┬──────────────────┬──────┘
   │              │                  │                  │
   ▼              ▼                  ▼                  ▼
┌────────┐  ┌──────────┐    ┌────────────┐    ┌──────────────┐
│Postgres│  │qBittorrent│    │  Jackett   │    │ FlareSolverr │
│  5432  │  │   8082    │    │   9117     │    │    8191      │
└────────┘  └──────────┘    └────────────┘    └──────────────┘
                                                          │
                                                          ▼
                                                  ┌──────────────┐
                                                  │   Jellyfin   │
                                                  │  (Windows)   │
                                                  │    8096      │
                                                  └──────────────┘
```

**Nota:** qBittorrent, Jackett e FlareSolverr rodam como containers Docker. O Jellyfin permanece no Windows (serviço externo). Caddy atua como reverse proxy na porta 80. Avahi mDNS resolve `jellyfin.local` na rede local.

---

## Tecnologias

### Backend
- **FastAPI** 0.109.0 — Framework web de alta performance com validação automática via Pydantic
- **Uvicorn** 0.27.0 — Servidor ASGI para execução assíncrona
- **SQLAlchemy** 2.0.25 — ORM para banco de dados
- **Alembic** 1.13.1 — Migrações de banco de dados
- **PostgreSQL** — Banco de dados relacional
- **httpx** — Cliente HTTP assíncrono para integrações externas
- **Loguru + Structlog** — Logging estruturado
- **WebSockets** — Comunicação em tempo real para monitoramento

### Frontend
- **React** 18 — Biblioteca UI com hooks e componentes funcionais
- **TypeScript** — Tipagem estática
- **Vite** — Build tool rápida
- **TailwindCSS** — Estilização utilitária
- **TanStack Query** — Gerenciamento de estado server-side e cache
- **Axios** — Cliente HTTP

---

## Pré-requisitos

- Docker e Docker Compose
- Jellyfin Server (no Windows ou outro host)
- TMDB API Key (gratuito em https://www.themoviedb.org/settings/api)

**Para desenvolvimento local (sem Docker):**
- Python 3.12+
- Node.js 20+
- PostgreSQL 15+

---

## Instalação via Docker (Recomendado)

### 1. Clone o repositório

```bash
git clone <repo-url>
cd jellyfin_automation
```

### 2. Configure o ambiente

```bash
cp .env.example .env
# Edite .env com suas configurações (API keys, caminhos de mídia, etc.)
```

### 3. Inicie os serviços

```bash
docker-compose up --build -d
```

Serviços expostos:

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Frontend | `http://localhost:3001` | Interface web |
| Caddy | `http://localhost:80` | Reverse proxy |
| Backend API | `http://localhost:8000` | API REST + Swagger |
| qBittorrent | `http://localhost:8082` | Gerenciador de torrents |
| Jackett | `http://localhost:9117` | Indexador de torrents |
| FlareSolverr | `http://localhost:8191` | Bypass Cloudflare |
| PostgreSQL | `localhost:5432` | Banco de dados |

---

## Configuração Pós-Instalação

Após iniciar os containers, é necessário configurar os serviços. As configurações são salvas no banco de dados e podem ser gerenciadas pela interface web.

### 1. Configurar API Keys (pela UI)

Acesse `http://localhost:3001/settings` e preencha:

| Campo | Descrição |
|-------|-----------|
| TMDB API Key | Chave da API do TMDB |
| OMDB API Key | Chave da API do OMDB (opcional, para Rotten Tomatoes) |
| Jackett URL | `http://jackett:9117` (Docker) ou `http://localhost:9117` (local) |
| Jackett API Key | Copiada da UI do Jackett |
| qBittorrent Host | `http://qbittorrent:8080` (Docker) ou `http://localhost:8082` (local) |
| qBittorrent Username | Usuário do qBittorrent |
| qBittorrent Password | Senha do qBittorrent |
| Jellyfin URL | `http://host.docker.internal:8096` (Docker) ou `http://localhost:8096` (local) |
| Jellyfin API Key | Criada no Dashboard do Jellyfin |

### 2. Configurar Jackett

1. Acesse `http://localhost:9117`
2. **Adicione indexadores** de torrent (ex: 1337x, ThePirateBay, etc.)
3. **Configure o FlareSolverr:**
   - Clique em **Config** (ícone de engrenagem)
   - No campo **FlareSolverr API URL**, coloque: `http://flaresolverr:8191`
   - Clique em **Save**
4. **Copie a API Key** (canto superior direito)
5. Cole a API Key na página de Configurações do app

### 3. Configurar qBittorrent

Na primeira execução, o qBittorrent gera uma **senha temporária**. Para definir uma senha permanente:

1. Acesse `http://localhost:8082`
2. Faça login com `admin` e a senha temporária (veja nos logs: `docker compose logs qbittorrent | grep "temporary password"`)
3. Vá em **Settings → Web UI → Authentication**
4. Defina uma senha fixa
5. Atualize a senha na página de Configurações do app

### 4. Configurar Jellyfin

1. Acesse o Jellyfin em `http://localhost:8096`
2. Crie uma **API Key** em Dashboard → Advanced → API Keys
3. Configure as pastas de biblioteca para apontar para os mesmos caminhos definidos em `MOVIES_PATH`, `SERIES_PATH`, `ANIMES_PATH`

### 5. Configurar Caminhos de Mídia

Na página de Configurações do app, defina os caminhos absolutos onde os arquivos serão organizados:

| Campo | Exemplo |
|-------|---------|
| Pasta de Filmes | `/mnt/d/Filmes` |
| Pasta de Séries | `/mnt/d/Séries` |
| Pasta de Animes | `/mnt/d/Animes` |

---

## Instalação Manual (Desenvolvimento)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Execute as migrações
alembic upgrade head

# Inicie o servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # Modo desenvolvimento (porta 3001)
npm run build      # Build de produção
```

### 3. Serviços externos

Quando rodando fora do Docker, você precisa ter qBittorrent, Jackett e FlareSolverr instalados e configurados separadamente. Atualize as URLs no `.env` ou na página de Configurações para apontar para `localhost`.

---

## Uso

### Interface Web

Acesse `http://localhost:3001` para a interface web.

#### Buscar Conteúdo
1. Digite o nome do filme/série/anime na barra de busca
2. Clique no card para ver torrents disponíveis
3. Clique em **Download** para adicionar à fila

#### Monitorar Downloads
- Acesse a aba **Downloads**
- Acompanhe progresso, velocidade e ETA em tempo real
- Use **Pausar**, **Continuar** ou **Cancelar** para gerenciar

#### Configurações
- Acesse **Configurações** para ajustar caminhos de mídia, preferências de download e chaves de API

### API REST

A documentação interativa da API está disponível em:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### WebSocket

Conecte-se ao WebSocket em `ws://localhost:8000/ws` para receber atualizações em tempo real sobre downloads.

---

## Testes

### Backend

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run build
```

O build deve completar sem erros de TypeScript.

---

## API

### Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/search/?q={query}` | Buscar no TMDB |
| GET | `/api/search/torrents` | Buscar torrents via Jackett |
| GET | `/api/discover/sections/` | Catálogo de seções Discover |
| GET | `/api/discover/sections/{id}/` | Dados de uma seção Discover |
| GET | `/api/discover/genres/` | Lista de gêneros TMDB |
| GET | `/api/discover/providers/` | Lista de provedores de streaming |
| GET | `/api/downloads/` | Listar downloads |
| POST | `/api/downloads/` | Criar novo download |
| DELETE | `/api/downloads/{id}` | Cancelar download |
| POST | `/api/downloads/{id}/pause` | Pausar no qBittorrent |
| POST | `/api/downloads/{id}/resume` | Continuar no qBittorrent |
| GET | `/api/filesystem/browse` | Explorar sistema de arquivos |
| GET | `/api/settings/` | Obter configurações |
| PUT | `/api/settings/{key}` | Atualizar configuração |
| GET | `/api/logs/` | Obter logs estruturados |
| GET | `/health` | Health check da aplicação |
| WS | `/ws` | WebSocket para updates em tempo real |

---

## WebSocket

O backend expõe um endpoint WebSocket em `/ws` que envia atualizações JSON sobre o estado dos downloads:

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

---

## Contribuição

1. Fork o repositório
2. Crie uma branch: `git checkout -b feature/nova-feature`
3. Commit suas mudanças: `git commit -am 'Adiciona nova feature'`
4. Push para a branch: `git push origin feature/nova-feature`
5. Abra um Pull Request

### Convenções de Código
- Backend: PEP 8, type hints obrigatórios
- Frontend: ESLint + Prettier configurados
- Commits em português ou inglês

---

## Licença

MIT License
