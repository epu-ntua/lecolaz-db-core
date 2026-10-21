import { Link } from 'react-router-dom';
import { MapPinOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/layout/EmptyState';
import { PageContainer } from '@/components/layout/PageContainer';

export default function NotFoundPage() {
  return (
    <PageContainer>
      <EmptyState
        icon={MapPinOff}
        title="This page could not be found"
        description="The address may have changed, or the page is not part of this workspace."
        action={
          <Button asChild>
            <Link to="/overview">Return to overview</Link>
          </Button>
        }
      />
    </PageContainer>
  );
}
