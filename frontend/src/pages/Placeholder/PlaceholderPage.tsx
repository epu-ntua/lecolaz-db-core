import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { EmptyState } from '@/components/layout/EmptyState';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';

type PlaceholderPageProps = {
  eyebrow?: string;
  title: string;
  description: string;
  icon: LucideIcon;
  emptyTitle?: string;
  action?: ReactNode;
};

export default function PlaceholderPage({
  eyebrow = 'Workspace',
  title,
  description,
  icon,
  emptyTitle,
  action,
}: PlaceholderPageProps) {
  return (
    <PageContainer className="space-y-8">
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <EmptyState
        icon={icon}
        title={emptyTitle ?? `${title} is ready for the next phase`}
        description="This area is intentionally lightweight in Phase 1 while the building experience and application foundation are established."
        action={action}
      />
    </PageContainer>
  );
}
