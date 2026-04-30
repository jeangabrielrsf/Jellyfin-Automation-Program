import React from 'react';
import { Link } from 'react-router-dom';
import { Search, Download, Settings } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

const HomePage: React.FC = () => {
  const features = [
    {
      title: 'Buscar Conteúdo',
      description: 'Pesquise filmes, séries e animes no TMDB',
      icon: Search,
      link: '/search',
    },
    {
      title: 'Downloads',
      description: 'Monitore e gerencie seus downloads',
      icon: Download,
      link: '/downloads',
    },
    {
      title: 'Configurações',
      description: 'Configure paths, APIs e preferências',
      icon: Settings,
      link: '/settings',
    },
  ];

  return (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold">Bem-vindo ao Jellyfin Automation</h2>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Automatize a busca, download e organização de conteúdo para seu servidor Jellyfin.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature) => (
          <Link key={feature.title} to={feature.link}>
            <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
              <CardHeader>
                <feature.icon className="w-8 h-8 mb-2 text-primary" />
                <CardTitle>{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{feature.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default HomePage;
