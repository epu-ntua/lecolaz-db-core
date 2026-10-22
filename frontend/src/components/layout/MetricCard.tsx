import type { LucideIcon } from 'lucide-react';

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-xl border bg-card p-3 sm:p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] sm:text-xs font-medium text-muted-foreground">
          {label}
        </p>
        <Icon className="hidden h-4 w-4 shrink-0 text-primary/70 sm:block" />
      </div>
      <p className="mt-3 text-2xl sm:mt-4 sm:text-3xl font-semibold tabular-nums tracking-tight">
        {value}
      </p>
      <p className="mt-1.5 hidden text-xs sm:block text-muted-foreground">{detail}</p>
    </div>
  );
}
