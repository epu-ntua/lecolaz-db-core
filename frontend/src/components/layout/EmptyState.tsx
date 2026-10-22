import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-[260px] flex-col items-center justify-center rounded-xl border bg-card px-6 py-10 text-center">
      <div className="mb-5 rounded-xl border bg-muted p-3 text-primary shadow-sm">
        <Icon className="h-7 w-7" />
      </div>
      <h2 className="text-base font-semibold tracking-tight">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
