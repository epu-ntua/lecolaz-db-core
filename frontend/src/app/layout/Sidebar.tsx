import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { navigation } from '@/app/navigation';
import { cn } from '@/lib/utils';

type SidebarProps = { mobileOpen: boolean; onMobileOpenChange: (open: boolean) => void };

export default function PlatformSidebar({
  mobileOpen,
  onMobileOpenChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { pathname } = useLocation();
  const content = (compact: boolean) => (
    <>
      <div className="flex h-24 shrink-0 items-center justify-center px-3">
        <NavLink
          to="/overview"
          onClick={() => onMobileOpenChange(false)}
          aria-label="Le’Colaz overview"
          className={cn(
            'flex items-center justify-center rounded-lg bg-brand-surface p-2',
            compact ? 'h-12 w-12' : 'h-14 w-40',
          )}
        >
          <img
            src="/logo_green_transparent.png"
            alt="Le’Colaz"
            className="max-h-full w-full object-contain"
          />
        </NavLink>
      </div>
      <nav
        aria-label="Main navigation"
        className="flex-1 space-y-7 overflow-y-auto px-3 py-4"
      >
        {['Workspace', 'Management'].map((group) => (
          <div key={group}>
            {!compact && (
              <p className="mb-3 px-3 text-[10px] font-medium uppercase tracking-[0.18em] text-sidebar-muted">
                {group}
              </p>
            )}
            <ul className="space-y-1">
              {navigation
                .filter((item) => item.group === group)
                .map((item) => (
                  <li key={item.url}>
                    <NavLink
                      to={item.url}
                      title={compact ? item.title : undefined}
                      aria-label={compact ? item.title : undefined}
                      onClick={() => onMobileOpenChange(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex min-h-10 items-center gap-3 rounded-lg px-3 text-[13px] font-medium text-sidebar-muted transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground',
                          compact && 'justify-center px-2',
                          (isActive || (pathname === '/' && item.url === '/overview')) &&
                            'bg-sidebar-accent text-sidebar-primary ring-1 ring-inset ring-sidebar-border',
                        )
                      }
                    >
                      <item.icon className="h-[18px] w-[18px] shrink-0" />
                      {!compact && <span>{item.title}</span>}
                    </NavLink>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </nav>
    </>
  );
  return (
    <>
      <aside
        className={cn(
          'hidden shrink-0 flex-col border-r border-sidebar-border bg-sidebar-background text-sidebar-foreground lg:flex',
          collapsed ? 'w-[76px]' : 'w-[248px]',
        )}
      >
        {content(collapsed)}
        <div className="border-t border-sidebar-border p-3">
          <Button
            variant="ghost"
            className="w-full text-xs text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <>
                <PanelLeftClose className="h-4 w-4" /> Collapse navigation
              </>
            )}
          </Button>
        </div>
      </aside>
      <Dialog open={mobileOpen} onOpenChange={onMobileOpenChange}>
        <DialogContent className="left-0 top-0 flex h-dvh max-h-dvh w-[280px] translate-x-0 translate-y-0 flex-col gap-0 rounded-none border-sidebar-border bg-sidebar-background p-0 text-sidebar-foreground">
          <DialogTitle className="sr-only">Navigation</DialogTitle>
          <DialogDescription className="sr-only">
            Navigate the Le’Colaz workspace.
          </DialogDescription>
          {content(false)}
        </DialogContent>
      </Dialog>
    </>
  );
}
