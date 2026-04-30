# Guia de Instalação — Jellyfin Automation

Este guia cobre **3 abordagens** para rodar o projeto no Windows. Escolha a que melhor se adapta ao seu ambiente.

---

## 📋 Índice

1. [Opção 1: Docker + WSL2 (Recomendada)](#opção-1-docker--wsl2-recomendada)
2. [Opção 2: WSL2 Nativo](#opção-2-wsl2-nativo)
3. [Opção 3: Windows Nativo](#opção-3-windows-nativo)
4. [Troubleshooting Comum](#troubleshooting-comum)

---

## Opção 1: Docker + WSL2 (Recomendada)

**Quando usar:** Você já tem WSL2 instalado e quer o setup mais limpo e isolado. O Docker gerencia PostgreSQL, backend e frontend automaticamente.

### Pré-requisitos

| Software | Download | Observação |
|----------|----------|------------|
| Docker Desktop | [docker.com](https://www.docker.com/products/docker-desktop/) | Ativar integração com WSL2 nas configurações |
| Git (WSL2) | `sudo apt install git` dentro do WSL2 | |
| qBittorrent | [qbittorrent.org](https://www.qbittorrent.org/download) | No Windows, com Web UI habilitada |
| Jackett | [GitHub releases](https://github.com/Jackett/Jackett/releases) | No Windows |
| Jellyfin | [jellyfin.org](https://jellyfin.org/downloads/) | No Windows |

### Passo a passo

#### 1. Clone o projeto no WSL2

Abra um terminal **Ubuntu (WSL2)**:

```bash
cd ~
git clone <repo-url>
cd jellyfin_automation
```

#### 2. Configure o ambiente

```bash
cp .env.example .env
nano .env
```

Edite o `.env` com os valores corretos:

```ini
# Banco de dados (roda no container Docker)
DATABASE_URL=postgresql://jfa_user:jfa_password@db:5432/jellyfin_automation

# TMDB — obtenha em https://www.themoviedb.org/settings/api
TMDB_API_KEY=sua_chave_aqui

# Serviços no Windows — host.docker.internal aponta para o Windows
QBITTORRENT_HOST=http://host.docker.internal:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=sua_senha_qbittorrent

JACKETT_URL=http://host.docker.internal:9117
JACKETT_API_KEY=sua_chave_jackett

JELLYFIN_URL=http://host.docker.internal:8096
JELLYFIN_API_KEY=sua_chave_jellyfin

# App
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
SECRET_KEY=uma-chave-secreta-forte

# Pastas de mídia no Windows — montadas via /mnt/
# Exemplo: D:\Filmes no Windows = /mnt/d/Filmes no WSL2
MOVIES_PATH=/mnt/d/Filmes
SERIES_PATH=/mnt/d/Séries
ANIMES_PATH=/mnt/d/Animes

# Preferências padrão
DEFAULT_QUALITY=1080p
DEFAULT_LANGUAGE=legendado
```

> **Importante:** Ajuste `/mnt/d/Filmes` para a letra do seu drive e nome correto das pastas. Use sempre barras `/` no Linux.

#### 3. Configure as pastas no Jellyfin (Windows)

No Jellyfin Server (Windows), verifique se as bibliotecas apontam para as mesmas pastas:
- Filmes → `D:\Filmes`
- Séries → `D:\Séries`
- Animes → `D:\Animes`

#### 4. Suba os containers

```bash
docker-compose up --build -d
```

O primeiro build pode levar alguns minutos.

#### 5. Verifique o status

```bash
docker-compose ps
docker-compose logs -f backend
```

#### 6. Acesse a aplicação

- **Frontend:** http://localhost:3000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Backend:** http://localhost:8000

#### Comandos úteis

```bash
# Ver logs em tempo real
docker-compose logs -f backend
docker-compose logs -f frontend

# Parar todos os serviços
docker-compose down

# Parar e remover volumes (apaga o banco!)
docker-compose down -v

# Rebuild após alterações no código
docker-compose up --build -d

# Entrar no container do backend
 docker-compose exec backend bash
```

---

## Opção 2: WSL2 Nativo

**Quando usar:** Você quer rodar o backend e frontend diretamente no Linux (WSL2), sem Docker. Oferece mais controle e é idêntico ao ambiente de desenvolvimento.

### Pré-requisitos

| Software | Instalação |
|----------|------------|
| WSL2 + Ubuntu | `wsl --install` no PowerShell (admin) |
| Python 3.12 | `sudo apt update && sudo apt install python3.12 python3.12-venv python3-pip` |
| Node.js 20 | [NodeSource](https://github.com/nodesource/distributions) ou [nvm](https://github.com/nvm-sh/nvm) |
| PostgreSQL 15 | `sudo apt install postgresql postgresql-contrib` |
| qBittorrent | [qbittorrent.org](https://www.qbittorrent.org/download) (Windows ou WSL2) |
| Jackett | [GitHub releases](https://github.com/Jackett/Jackett/releases) (Windows ou WSL2) |
| Jellyfin | [jellyfin.org](https://jellyfin.org/downloads/) (Windows ou WSL2) |

### Passo a passo

#### 1. Configure o PostgreSQL no WSL2

```bash
# Inicie o serviço
sudo service postgresql start

# Crie o usuário e banco
sudo -u postgres psql -c "CREATE USER jfa_user WITH PASSWORD 'jfa_password';"
sudo -u postgres psql -c "CREATE DATABASE jellyfin_automation OWNER jfa_user;"
```

#### 2. Clone o projeto

```bash
cd ~
git clone <repo-url>
cd jellyfin_automation
```

#### 3. Configure o ambiente

```bash
cp .env.example .env
nano .env
```

```ini
DATABASE_URL=postgresql://jfa_user:jfa_password@localhost:5432/jellyfin_automation
TMDB_API_KEY=sua_chave_aqui
QBITTORRENT_HOST=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=sua_senha
JACKETT_URL=http://localhost:9117
JACKETT_API_KEY=sua_chave_jackett
JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=sua_chave_jellyfin
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
SECRET_KEY=uma-chave-secreta-forte
MOVIES_PATH=/mnt/d/Filmes
SERIES_PATH=/mnt/d/Séries
ANIMES_PATH=/mnt/d/Animes
DEFAULT_QUALITY=1080p
DEFAULT_LANGUAGE=legendado
```

> Se qBittorrent/Jackett/Jellyfin estiverem no **Windows**, use `host.docker.internal` não funciona fora do Docker. Use o **IP da sua máquina na rede local** (ex: `http://192.168.1.100:8080`) ou configure os serviços no WSL2 também.

#### 4. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 5. Frontend (outro terminal WSL2)

```bash
cd ~/jellyfin_automation/frontend
npm install
npm run dev
```

#### 6. Acesse

- **Frontend:** http://localhost:5173 (porta padrão do Vite dev server)
- **API Docs:** http://localhost:8000/docs

#### Comandos úteis

```bash
# Iniciar PostgreSQL
sudo service postgresql start

# Ativar venv do backend
source backend/venv/bin/activate

# Rodar testes do backend
cd backend && pytest tests/ -v

# Build de produção do frontend
cd frontend && npm run build
```

---

## Opção 3: Windows Nativo

**Quando usar:** Você não quer usar WSL2 nem Docker. Tudo roda diretamente no Windows.

### Pré-requisitos

| Software | Download | Observação |
|----------|----------|------------|
| Python 3.12 | [python.org](https://www.python.org/downloads/) | Marque "Add to PATH" na instalação |
| Node.js 20 | [nodejs.org](https://nodejs.org/) | Versão LTS |
| PostgreSQL 15 | [postgresql.org](https://www.postgresql.org/download/windows/) | Inclui pgAdmin |
| Git for Windows | [git-scm.com](https://git-scm.com/download/win) | |
| qBittorrent | [qbittorrent.org](https://www.qbittorrent.org/download) | |
| Jackett | [GitHub releases](https://github.com/Jackett/Jackett/releases) | |
| Jellyfin | [jellyfin.org](https://jellyfin.org/downloads/) | |

### Passo a passo

#### 1. Configure o PostgreSQL

1. Instale o PostgreSQL com o instalador oficial
2. Durante a instalação, defina uma senha para o usuário `postgres`
3. Abra o **pgAdmin 4** (instalado junto)
4. Crie o banco:
   - Servers → PostgreSQL → Databases (clique direito) → Create → Database
   - Nome: `jellyfin_automation`
   - Owner: `postgres`

Ou via SQL Shell (psql):
```sql
CREATE USER jfa_user WITH PASSWORD 'jfa_password';
CREATE DATABASE jellyfin_automation OWNER jfa_user;
```

#### 2. Clone o projeto

Abra o **PowerShell** ou **Git Bash**:

```powershell
cd C:\Projetos
git clone <repo-url>
cd jellyfin_automation
```

#### 3. Configure o ambiente

```powershell
copy .env.example .env
notepad .env
```

```ini
DATABASE_URL=postgresql://jfa_user:jfa_password@localhost:5432/jellyfin_automation
TMDB_API_KEY=sua_chave_aqui
QBITTORRENT_HOST=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=sua_senha
JACKETT_URL=http://localhost:9117
JACKETT_API_KEY=sua_chave_jackett
JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=sua_chave_jellyfin
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
SECRET_KEY=uma-chave-secreta-forte
MOVIES_PATH=C:\Filmes
SERIES_PATH=C:\Séries
ANIMES_PATH=C:\Animes
DEFAULT_QUALITY=1080p
DEFAULT_LANGUAGE=legendado
```

> Ajuste os caminhos `C:\Filmes` para onde suas mídias estão no Windows.

#### 4. Backend

No PowerShell:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 5. Frontend (outro terminal PowerShell)

```powershell
cd ..\frontend
npm install
npm run dev
```

#### 6. Acesse

- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs

#### Comandos úteis (PowerShell)

```powershell
# Ativar venv
backend\venv\Scripts\activate

# Rodar testes
pytest backend\tests -v

# Build frontend
cd frontend
npm run build
```

---

## Troubleshooting Comum

### Erro: "Cannot connect to the Docker daemon"
**Solução:** Certifique-se de que o Docker Desktop está aberto e rodando.

### Erro: "Connection refused" ao conectar no qBittorrent/Jackett/Jellyfin
**Causa:** O container/backend não consegue acessar o serviço no Windows.
**Soluções:**
- **Docker:** Use `host.docker.internal` ao invés de `localhost`
- **WSL2 Nativo:** Use o IP da sua máquina na rede local (ex: `192.168.1.100`)
- **Windows Nativo:** Verifique se o serviço está rodando e a porta está correta

### Erro: "Permission denied" nas pastas de mídia (Docker/WSL2)
**Causa:** O container não tem permissão para escrever nas pastas do Windows.
**Solução:** No PowerShell (admin):
```powershell
# Conceda permissão ao WSL2
icacls "D:\Filmes" /grant Everyone:F /T
```

### Erro: "Module not found" no frontend
**Causa:** Dependências não instaladas.
**Solução:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Erro: "alembic: command not found"
**Causa:** O ambiente virtual não está ativado ou alembic não está instalado.
**Solução:**
```bash
# Linux/WSL2
source backend/venv/bin/activate
pip install alembic

# Windows
backend\venv\Scripts\activate
pip install alembic
```

### Como descobrir meu IP local
No PowerShell ou terminal:
```powershell
# Windows
ipconfig

# Linux/WSL2
ip addr show | grep "inet "
```
Procure pelo endereço que começa com `192.168.x.x` ou `10.x.x.x`.

---

## 🎯 Resumo das Portas

| Serviço | Porta | URL |
|---------|-------|-----|
| Frontend | 3000 (Docker) / 5173 (dev) | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000/docs | http://localhost:8000/docs |
| PostgreSQL | 5432 | localhost:5432 |
| qBittorrent Web UI | 8080 | http://localhost:8080 |
| Jackett | 9117 | http://localhost:9117 |
| Jellyfin | 8096 | http://localhost:8096 |

---

## 📞 Precisa de ajuda?

Se encontrar algum problema não listado aqui:
1. Verifique os logs: `docker-compose logs` (Opção 1) ou terminal de execução (Opções 2 e 3)
2. Confira se todas as variáveis no `.env` estão preenchidas corretamente
3. Certifique-se de que qBittorrent, Jackett e Jellyfin estão rodando e acessíveis
