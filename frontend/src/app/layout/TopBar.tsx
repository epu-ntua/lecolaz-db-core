import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Menu, Search, ArrowUpRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { SearchInput } from '@/components/ui/search-input';
import { navigation } from '@/app/navigation';

export default function TopBar({ onMenuClick }: { onMenuClick: () => void }) {
  const { pathname } = useLocation();
  const current =
    navigation.find((item) => pathname.startsWith(item.url)) ?? navigation[0];
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        setOpen((value) => !value);
      }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);
  const matches = navigation.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <>
      <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b bg-card px-4 sm:px-7 lg:px-9">
        <div className="flex min-w-0 items-center gap-2 text-xs">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation"
            onClick={onMenuClick}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="hidden text-muted-foreground sm:inline">Workspace</span>
          <ChevronRight className="hidden h-3 w-3 text-muted-foreground sm:block" />
          <Link to={current.url} className="truncate font-medium">
            {current.title}
          </Link>
          {pathname.split('/').filter(Boolean).length > 1 && (
            <>
              <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
              <span className="text-muted-foreground">Details</span>
            </>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="shrink-0 text-muted-foreground"
          aria-label="Quick navigation"
          onClick={() => {
            setQuery('');
            setOpen(true);
          }}
        >
          <Search className="h-4 w-4" />
          <span className="hidden sm:inline">Go to…</span>
          <kbd className="ml-3 hidden rounded border px-1.5 py-0.5 text-[10px] md:block">
            Ctrl K
          </kbd>
        </Button>
      </header>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogTitle>Go to workspace</DialogTitle>
          <DialogDescription className="sr-only">
            Search and open a page.
          </DialogDescription>
          <SearchInput value={query} onChange={setQuery} placeholder="Find a page…" />
          <div className="space-y-1">
            {matches.map((item) => (
              <Link
                key={item.url}
                to={item.url}
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 rounded-lg p-3 text-sm hover:bg-accent focus:bg-accent"
              >
                <item.icon className="h-4 w-4 text-primary" />
                {item.title}
                <ArrowUpRight className="ml-auto h-3.5 w-3.5 text-muted-foreground" />
              </Link>
            ))}
            {!matches.length && (
              <p className="p-4 text-sm text-muted-foreground">No matching pages.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
