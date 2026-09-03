import { useEffect } from 'react';

export const useSmoothScroll = () => {
  useEffect(() => {
    // Enable smooth scrolling natively across root
    document.documentElement.style.scrollBehavior = 'smooth';
    return () => {
      document.documentElement.style.scrollBehavior = 'auto';
    };
  }, []);
};
