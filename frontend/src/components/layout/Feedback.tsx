import { AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function ErrorNotice({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
    >
      <AlertCircle className="h-4 w-4 shrink-0" />
      <p className="min-w-0 flex-1">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div
      role="status"
      className="flex min-h-32 items-center justify-center gap-3 rounded-xl border bg-card p-6 text-sm text-muted-foreground"
    >
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}
