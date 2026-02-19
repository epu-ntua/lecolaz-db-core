import { useState } from "react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Database,
  Search,
  Box,
  Bell,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const modules = [
  { title: "Dashboard", url: "/dashboard", icon: LayoutDashboard },
  { title: "Data Discovery", url: "/data-discovery", icon: Database },
  { title: "Querying & Analytics", url: "/querying-analytics", icon: Search },
  { title: "BIM & Assets", url: "/bim", icon: Box },
  { title: "Alerts & Events", url: "/alerts", icon: Bell },
  { title: "Governance & Reporting", url: "/governance-reporting", icon: FileText },
  { title: "Admin Panel", url: "/admin", icon: Settings },
];

export default function PlatformSidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "h-screen flex flex-col border-r transition-all duration-300 ease-in-out bg-sidebar-background text-sidebar-foreground border-sidebar-border",
        collapsed ? "w-20" : "w-72"
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-3 border-b border-sidebar-border">
        <div className="w-full overflow-hidden flex justify-center">
          <div className="rounded-md bg-white p-1.5">
            <img
              src="/logo_green_transparent.png"
              alt="LeColaz logo"
              className={cn(
                "object-contain",
                collapsed ? "w-8 h-8" : "w-36 h-8"
              )}
            />
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto scrollbar-thin">
        <ul className="space-y-1 px-2">
          {modules.map((module) => (
            <li key={module.url}>
              <NavLink
                to={module.url}
                end={module.url === "/dashboard"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-md transition-all duration-200 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    collapsed && "justify-center px-2",
                    isActive && "bg-sidebar-primary text-sidebar-primary-foreground font-medium shadow-sm"
                  )
                }
              >
                <module.icon className="w-5 h-5 flex-shrink-0" />

                {!collapsed && (
                  <span className="text-sm truncate">
                    {module.title}
                  </span>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse Toggle */}
      <div className="p-3 border-t border-sidebar-border">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs">Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
