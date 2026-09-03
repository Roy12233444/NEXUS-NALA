import { useEffect } from 'react';

export const useLenisScroll = () => {
  useEffect(() => {
    // Native browser smooth scroll - 100% reliable, zero scroll freeze
    document.documentElement.style.scrollBehavior = 'smooth';
    document.body.style.scrollBehavior = 'smooth';

    return () => {
      document.documentElement.style.scrollBehavior = 'auto';
      document.body.style.scrollBehavior = 'auto';
    };
  }, []);
};
