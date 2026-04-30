# Jellyfin Automation

Aplicação full-stack para automação de downloads de filmes, séries e animes, com organização automática de bibliotecas e integração com Jellyfin.

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Testes](#testes)
- [Deploy](#deploy)
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
│                     Porta: 3000                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│            (FastAPI + SQLAlchemy + Uvicorn)                 │
│                     Porta: 8000                              │
└──┬───────────────────┬───────────────────┬──────────────────┘
   │                   │                   │
   ▼                   ▼                   ▼
┌────────┐     ┌────────────┐     ┌─────────────────┐
│PostgreSQL│     │  qBittorrent │     │    Jellyfin     │
│ 5432   │     │    8080      │     │     8096        │
└────────┘     └────────────┘     └─────────────────┘
   │
   ▼
┌────────────┐
│   Jackett   │
│   9117      │
└────────────┘
```

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

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- qBittorrent com Web UI habilitado
- Jackett configurado com indexadores
- Jellyfin Server
- TMDB API Key (gratuito em https://www.themoviedb.org/settings/api)

---

## Instalação

### 1. Clone o repositório

```bash
git clone <repo-url>
cd jellyfin_automation
```

### 2. Configure o ambiente

```bash
cp .env.example .env
# Edite .env com suas configurações
```

### 3. Backend

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

### 4. Frontend

```bash
cd frontend
npm install
npm run dev        # Modo desenvolvimento
npm run build      # Build de produção
```

---

## Configuração

### Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | URL do PostgreSQL | `postgresql://user:pass@localhost/db` |
| `TMDB_API_KEY` | Chave API do TMDB | `abc123...` |
| `QBITTORRENT_HOST` | URL do qBittorrent Web UI | `http://localhost:8080` |
| `QBITTORRENT_USERNAME` | Usuário do qBittorrent | `admin` |
| `QBITTORRENT_PASSWORD` | Senha do qBittorrent | `adminadmin` |
| `JACKETT_URL` | URL do Jackett | `http://localhost:9117` |
| `JACKETT_API_KEY` | Chave API do Jackett | `xyz789...` |
| `JELLYFIN_URL` | URL do Jellyfin | `http://localhost:8096` |
| `JELLYFIN_API_KEY` | Chave API do Jellyfin | `def456...` |
| `MOVIES_PATH` | Pasta de filmes | `/media/movies` |
| `SERIES_PATH` | Pasta de séries | `/media/series` |
| `ANIMES_PATH` | Pasta de animes | `/media/animes` |
| `LOG_LEVEL` | Nível de log | `INFO` |
| `SECRET_KEY` | Chave secreta para JWT | `change-me-in-production` |

### Configuração dos Serviços Externos

#### qBittorrent
1. Abra **Ferramentas → Opções → Web UI**
2. Habilitar "Web User Interface"
3. Definir usuário/senha
4. Permitir acesso sem senha da máquina local (opcional)

#### Jackett
1. Acesse `http://localhost:9117`
2. Adicione indexadores de torrent
3. Copie a **API Key** das configurações

#### Jellyfin
1. Acesse `http://localhost:8096`
2. Crie uma **API Key** em Dashboard → Advanced → API Keys
3. Configure as pastas de biblioteca para apontar para os mesmos caminhos definidos em `MOVIES_PATH`, `SERIES_PATH`, `ANIMES_PATH`

---

## Uso

### Interface Web

Acesse `http://localhost:3000` para a interface web.

#### Buscar Conteúdo
1. Digite o nome do filme/série/anime na barra de busca
2. Clique no card para ver torrents disponíveis
3. Clique em **Download** para adicionar à fila

#### Monitorar Downloads
- Acesse a aba **Downloads**
- Acompanhe progresso, velocidade e ETA em tempo real
- Use **Pausar**, **Continuar** ou **Cancelar** para gerenciar

#### Configurações
- Acesse **Configurações** para ajustar qualidade padrão, idioma e paths

### API REST

A documentação interativa da API está disponível em:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### WebSocket

Conecte-se ao WebSocket em `ws://localhost:8000/api/ws` para receber atualizações em tempo real sobre downloads.

---

## Testes

### Backend

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

Cobertura atual: **45 testes** cobrindo configurações, logging, serviços (TMDB, qBittorrent, organizador, Jellyfin), scrapers, e routers.

### Frontend

```bash
cd frontend
npm run build
```

O build deve completar sem erros de TypeScript.

---

## Deploy

### Docker Compose (Recomendado)

```bash
# Configure as variáveis no .env
cp .env.example .env
nano .env

# Inicie todos os serviços
docker-compose up --build -d
```

Serviços expostos:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

### Estrutura de Pastas para Docker

As pastas de mídia são montadas como volumes:

```yaml
volumes:
  - ${MOVIES_PATH:-./media/movies}:/movies
  - ${SERIES_PATH:-./media/series}:/series
  - ${ANIMES_PATH:-./media/animes}:/animes
```

Certifique-se de que o usuário do container tem permissão de escrita nessas pastas.

---

## API

### Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/search/?q={query}` | Buscar no TMDB |
| GET | `/api/search/torrents` | Buscar torrents via Jackett |
| GET | `/api/downloads` | Listar downloads |
| POST | `/api/downloads` | Criar novo download |
| DELETE | `/api/downloads/{id}` | Cancelar download |
| POST | `/api/downloads/{id}/pause` | Pausar no qBittorrent |
| POST | `/api/downloads/{id}/resume` | Continuar no qBittorrent |
| GET | `/api/settings` | Obter configurações |
| PUT | `/api/settings/{key}` | Atualizar configuração |
| GET | `/api/logs` | Obter logs estruturados |
| WS | `/api/ws` | WebSocket para updates em tempo real |

---

## WebSocket

O backend expõe um endpoint WebSocket em `/api/ws` que envia atualizações JSON sobre o estado dos downloads:

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
