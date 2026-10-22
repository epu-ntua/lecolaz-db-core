import type { ReactNode } from 'react';

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-5 pb-2 md:flex-row md:items-center md:justify-between">
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <p className="section-label mb-2">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold tracking-[-0.04em] sm:text-[30px] sm:leading-tight">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </header>
  );
}
