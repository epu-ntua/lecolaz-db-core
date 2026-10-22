import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type PageContainerProps = {
  children: ReactNode;
  className?: string;
  size?: 'default' | 'wide';
};

export function PageContainer({
  children,
  className,
  size = 'default',
}: PageContainerProps) {
  return (
    <div
      className={cn(
        'mx-auto w-full px-4 py-6 sm:px-7 sm:py-8 lg:px-9',
        size === 'wide' ? 'max-w-[1520px]' : 'max-w-7xl',
        className,
      )}
    >
      {children}
    </div>
  );
}
