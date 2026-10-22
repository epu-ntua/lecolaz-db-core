import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
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
        title={emptyTitle ?? `${title} is not available yet`}
        description="This workspace is under development. You can continue exploring building models and their datasets in the available workspaces."
        action={
          action ?? (
            <div className="flex flex-wrap justify-center gap-3">
              <Button asChild variant="outline">
                <Link to="/buildings">Explore buildings</Link>
              </Button>
              <Button asChild variant="ghost">
                <Link to="/data">Open data explorer</Link>
              </Button>
            </div>
          )
        }
      />
    </PageContainer>
  );
}
