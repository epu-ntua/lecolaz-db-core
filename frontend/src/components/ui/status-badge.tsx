import { Badge } from './badge';
import { cn } from '@/lib/utils';

export function StatusBadge({ status }: { status: string | null }) {
  const failed = status === 'failed';
  const ready = status === 'processed';
  return (
    <Badge
      variant={failed ? 'destructive' : ready ? 'default' : 'secondary'}
      className="gap-1.5 whitespace-nowrap font-medium capitalize"
    >
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          failed ? 'bg-destructive' : ready ? 'bg-primary' : 'bg-muted-foreground',
        )}
      />
      {status ?? 'Unknown'}
    </Badge>
  );
}
