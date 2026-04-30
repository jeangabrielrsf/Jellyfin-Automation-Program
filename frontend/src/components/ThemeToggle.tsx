import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="relative w-10 h-10 rounded-full glass flex items-center justify-center
                 transition-all duration-400 hover:glow-primary-sm hover:scale-105
                 active:scale-95"
      aria-label={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
    >
      <Sun
        className={`w-5 h-5 text-primary absolute transition-all duration-400
                    ${theme === 'dark' ? 'rotate-90 opacity-0 scale-50' : 'rotate-0 opacity-100 scale-100'}`}
      />
      <Moon
        className={`w-5 h-5 text-primary absolute transition-all duration-400
                    ${theme === 'dark' ? 'rotate-0 opacity-100 scale-100' : '-rotate-90 opacity-0 scale-50'}`}
      />
    </button>
  );
};
