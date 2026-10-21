import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity,
  Blocks,
  Building2,
  ChevronLeft,
  ChevronRight,
  Database,
  FileBarChart,
  LayoutDashboard,
  Settings,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const primaryNavigation = [
  { title: 'Overview', url: '/overview', icon: LayoutDashboard },
  { title: 'Buildings & Pilots', url: '/buildings', icon: Building2 },
  { title: 'Components', url: '/components', icon: Blocks },
  { title: 'Monitoring & Performance', url: '/monitoring', icon: Activity },
  { title: 'Scenarios & Insights', url: '/scenarios', icon: FileBarChart },
  { title: 'Data Explorer', url: '/data', icon: Database },
];

const secondaryNavigation = [
  { title: 'Validation & Reports', url: '/reports', icon: FileBarChart },
  { title: 'Administration', url: '/administration', icon: Settings },
];

type SidebarProps = {
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
};

export default function PlatformSidebar({
  mobileOpen,
  onMobileOpenChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const renderNavigation = (items: typeof primaryNavigation) => (
    <ul className="space-y-1">
      {items.map((item) => (
        <li key={item.url}>
          <NavLink
            to={item.url}
            onClick={() => onMobileOpenChange(false)}
            className={({ isActive }) =>
              cn(
                'flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium text-sidebar-muted transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                collapsed && 'lg:justify-center lg:px-2',
                isActive &&
                  'bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary hover:text-sidebar-primary-foreground',
              )
            }
          >
            <item.icon className="h-[18px] w-[18px] shrink-0" />
            <span className={cn('truncate', collapsed && 'lg:hidden')}>{item.title}</span>
          </NavLink>
        </li>
      ))}
    </ul>
  );

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-foreground/35 backdrop-blur-sm lg:hidden"
          onClick={() => onMobileOpenChange(false)}
        />
      )}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex h-screen w-72 -translate-x-full flex-col border-r border-sidebar-border bg-sidebar-background text-sidebar-foreground transition-all duration-300 lg:static lg:translate-x-0',
          mobileOpen && 'translate-x-0',
          collapsed && 'lg:w-20',
        )}
      >
        <div className="relative flex h-24 shrink-0 items-center justify-center border-b border-sidebar-border px-3">
          <div
            className={cn(
              'flex h-16 w-44 items-center justify-center rounded-xl bg-white px-4 shadow-sm transition-all duration-300 lg:w-52',
              collapsed && 'lg:h-14 lg:w-14 lg:px-1.5',
            )}
          >
            <img
              src="/logo_green_transparent.png"
              alt="Le'Colaz"
              className={cn(
                'h-auto w-36 object-contain object-center transition-all duration-300 lg:w-44',
                collapsed && 'lg:w-12',
              )}
            />
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-2 text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground lg:hidden"
            onClick={() => onMobileOpenChange(false)}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="flex-1 space-y-7 overflow-y-auto px-3 py-6">
          <div>
            <p
              className={cn(
                'mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-sidebar-muted/70',
                collapsed && 'lg:hidden',
              )}
            >
              Workspace
            </p>
            {renderNavigation(primaryNavigation)}
          </div>
          <div>
            <p
              className={cn(
                'mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-sidebar-muted/70',
                collapsed && 'lg:hidden',
              )}
            >
              Management
            </p>
            {renderNavigation(secondaryNavigation)}
          </div>
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setCollapsed(!collapsed)}
            className="hidden w-full justify-center text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-accent-foreground lg:flex"
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4" />
                <span>Collapse navigation</span>
              </>
            )}
          </Button>
        </div>
      </aside>
    </>
  );
}
