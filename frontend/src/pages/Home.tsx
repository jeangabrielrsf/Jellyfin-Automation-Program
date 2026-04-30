import React from 'react';
import { Link } from 'react-router-dom';
import { Search, Download, Settings, ArrowRight } from 'lucide-react';

const features = [
  {
    title: 'Buscar Conteúdo',
    description: 'Pesquise filmes, séries e animes no TMDB com resultados instantâneos',
    icon: Search,
    link: '/search',
    color: 'from-orange-400/20 to-orange-600/10',
    iconColor: 'text-orange-400',
  },
  {
    title: 'Downloads',
    description: 'Monitore e gerencie seus downloads em tempo real',
    icon: Download,
    link: '/downloads',
    color: 'from-sky-400/20 to-sky-600/10',
    iconColor: 'text-sky-400',
  },
  {
    title: 'Configurações',
    description: 'Configure paths, APIs e preferências do sistema',
    icon: Settings,
    link: '/settings',
    color: 'from-emerald-400/20 to-emerald-600/10',
    iconColor: 'text-emerald-400',
  },
];

const HomePage: React.FC = () => {
  return (
    <div className="space-y-12 animate-fade-in">
      {/* Hero */}
      <section className="text-center space-y-6 py-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass
                      text-sm font-medium text-primary mb-4">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          Sistema ativo e pronto
        </div>
        <h1 className="font-display text-4xl md:text-5xl lg:text-6xl font-bold
                     text-foreground leading-tight">
          Bem-vindo ao{' '}
          <span className="text-gradient">Jellyfin Automation</span>
        </h1>
        <p className="text-muted-foreground text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          Automatize a busca, download e organização de conteúdo para seu servidor Jellyfin
          com uma experiência fluida e intuitiva.
        </p>
      </section>

      {/* Features Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature, index) => (
          <Link
            key={feature.title}
            to={feature.link}
            className="group relative"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <div className="relative h-full glass rounded-2xl p-6
                          transition-all duration-300
                          hover:-translate-y-1 hover:shadow-xl
                          hover:shadow-primary/5 hover:border-primary/20
                          overflow-hidden">
              {/* Background gradient */}
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0
                            group-hover:opacity-100 transition-opacity duration-500`} />

              <div className="relative z-10 space-y-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color}
                              flex items-center justify-center
                              group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className={`w-6 h-6 ${feature.iconColor}`} />
                </div>
                <div>
                  <h3 className="font-display text-xl font-bold text-foreground mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-primary text-sm font-medium
                              opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <span>Explorar</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </div>
          </Link>
        ))}
      </section>

      {/* Stats or decorative section */}
      <section className="glass rounded-2xl p-8 text-center">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-2">
            <div className="font-display text-3xl font-bold text-gradient">TMDB</div>
            <div className="text-muted-foreground text-sm">Busca de conteúdo</div>
          </div>
          <div className="space-y-2">
            <div className="font-display text-3xl font-bold text-gradient">Jackett</div>
            <div className="text-muted-foreground text-sm">Indexação de torrents</div>
          </div>
          <div className="space-y-2">
            <div className="font-display text-3xl font-bold text-gradient">qBittorrent</div>
            <div className="text-muted-foreground text-sm">Gerenciamento de downloads</div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
