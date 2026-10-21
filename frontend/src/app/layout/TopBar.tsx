import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';

type TopBarProps = { onMenuClick: () => void };

export default function TopBar({ onMenuClick }: TopBarProps) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-card/85 px-4 backdrop-blur sm:px-6">
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="Open navigation"
          onClick={onMenuClick}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <div>
          <p className="text-sm font-semibold tracking-tight">{"Le'Colaz Platform"}</p>
          <p className="hidden text-xs text-muted-foreground sm:block">
            Building intelligence workspace
          </p>
        </div>
      </div>
      <span className="rounded-full border bg-background px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
        Phase 1
      </span>
    </header>
  );
}
