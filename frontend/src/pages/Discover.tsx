import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { discoverAPI } from '../services/api';
import { DiscoverBanner } from '../components/DiscoverBanner';
import { DiscoverRow } from '../components/DiscoverRow';
import { SectionInfo } from '../types';

const BannerSkeleton: React.FC = () => (
  <div className="w-full h-[500px] md:h-[600px] rounded-xl bg-muted animate-shimmer mb-8" />
);

const DiscoverPage: React.FC = () => {
  const { data: catalog, isLoading: catalogLoading, isError: catalogError } = useQuery({
    queryKey: ['discover', 'sections'],
    queryFn: async () => {
      const res = await discoverAPI.getSections();
      return res.data;
    },
  });

  return (
    <div className="space-y-2 animate-fade-in">
      {catalogLoading && <BannerSkeleton />}
      {!catalogLoading && catalog?.banner && (
        <DiscoverBanner media={catalog.banner} />
      )}

      {catalogError && (
        <div className="text-center py-16">
          <p className="text-muted-foreground text-lg mb-4">
            Erro ao carregar seções
          </p>
          <button
            onClick={() => window.location.reload()}
            className="text-primary text-sm font-medium hover:underline"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {catalog && catalog.sections.map((section: SectionInfo) => (
        <DiscoverRow key={section.id} section={section} />
      ))}
    </div>
  );
};

export default DiscoverPage;
