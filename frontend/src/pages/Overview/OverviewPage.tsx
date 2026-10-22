import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ArrowUpRight,
  Building2,
  Database,
  Radio,
  FileText,
  ChartNoAxesCombined,
} from 'lucide-react';
import { listBimFiles } from '@/api/bim_files';
import { listRegisteredSensors } from '@/api/sensors';
import { listDatasets } from '@/api/datasets';
import type { DatasetDto } from '@/types/api/datasets';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { MetricCard } from '@/components/layout/MetricCard';
import { BuildingIllustration } from '@/components/layout/BuildingIllustration';

const workspaces = [
  {
    title: 'Building portfolio',
    description: 'Explore archetypes and living labs in 3D.',
    icon: Building2,
    href: '/buildings',
  },
  {
    title: 'Operational data',
    description: 'Discover sensors and connect them to buildings.',
    icon: Radio,
    href: '/monitoring',
  },
  {
    title: 'Simulation results',
    description: 'Inspect variables and time-series outputs.',
    icon: ChartNoAxesCombined,
    href: '/data?tab=simulations',
  },
];
export default function OverviewPage() {
  const [counts, setCounts] = useState<(number | null)[]>([null, null, null]);
  const [recent, setRecent] = useState<DatasetDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataError, setDataError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([listBimFiles(), listRegisteredSensors(), listDatasets()]).then(
      (results) => {
        if (cancelled) return;
        setCounts(
          results.map((result) =>
            result.status === 'fulfilled' ? result.value.length : null,
          ),
        );
        const datasets = results[2];
        if (datasets.status === 'fulfilled')
          setRecent(
            [...datasets.value]
              .sort(
                (a, b) =>
                  new Date(b.created_at ?? 0).getTime() -
                  new Date(a.created_at ?? 0).getTime(),
              )
              .slice(0, 4),
          );
        else setDataError(true);
        setLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);
  return (
    <PageContainer size="wide" className="space-y-7">
      <PageHeader
        eyebrow="Your workspace"
        title="Building intelligence, connected."
        description="A shared view of your buildings, their data and their performance."
      />
      <section className="grid overflow-hidden rounded-2xl border bg-card shadow-sm md:grid-cols-[1.15fr_1fr]">
        <div className="flex flex-col items-start justify-center p-7 lg:p-9">
          <p className="section-label text-primary">Le’Colaz digital workspace</p>
          <h2 className="mt-4 max-w-md text-3xl font-semibold leading-tight tracking-[-0.035em] lg:text-4xl">
            From building models to better decisions.
          </h2>
          <p className="mt-4 max-w-md text-sm leading-6 text-muted-foreground">
            Bring your physical and digital assets together. Start with a building,
            connect its data, and explore what it tells you.
          </p>
          <Button asChild className="mt-6">
            <Link to="/buildings">
              Explore portfolio <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
        <div className="blueprint relative flex min-h-56 items-center justify-center border-t bg-accent/50 md:border-l md:border-t-0">
          <BuildingIllustration className="w-full max-w-lg px-6" />
          <p className="absolute bottom-5 text-[10px] uppercase tracking-[0.24em] text-primary/70">
            Model · Connect · Understand
          </p>
        </div>
      </section>
      <section aria-label="Workspace summary" className="grid grid-cols-3 gap-3 sm:gap-4">
        {[
          {
            label: 'Building models',
            icon: Building2,
            detail: 'Archetypes and living labs',
          },
          { label: 'Registered sensors', icon: Radio, detail: 'Connected data sources' },
          {
            label: 'Available datasets',
            icon: Database,
            detail: 'Files in the data explorer',
          },
        ].map((item, index) => (
          <MetricCard
            key={item.label}
            label={item.label}
            icon={item.icon}
            value={counts[index] ?? '—'}
            detail={
              loading
                ? 'Loading workspace…'
                : counts[index] === null
                  ? 'Unable to load this summary'
                  : item.detail
            }
          />
        ))}
      </section>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-xl border bg-card">
          <div className="border-b px-5 py-4">
            <h2 className="text-sm font-semibold">Continue your work</h2>
          </div>
          <div className="p-2">
            {workspaces.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                className="group flex items-center gap-4 rounded-lg p-3 transition-colors hover:bg-muted"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border bg-background text-primary">
                  <item.icon className="h-[18px] w-[18px]" />
                </span>
                <div className="min-w-0">
                  <h3 className="text-sm font-medium">{item.title}</h3>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {item.description}
                  </p>
                </div>
                <ArrowUpRight className="ml-auto h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary" />
              </Link>
            ))}
          </div>
        </section>
        <section className="rounded-xl border bg-card">
          <div className="flex items-center justify-between border-b px-5 py-4">
            <h2 className="text-sm font-semibold">Recent uploads</h2>
            <Link to="/data" className="text-xs font-medium text-primary hover:underline">
              View all <span aria-hidden="true">↗</span>
            </Link>
          </div>
          {loading || dataError || !recent.length ? (
            <div className="flex min-h-48 flex-col items-center justify-center gap-3 p-6 text-center">
              <Database className="h-6 w-6 text-muted-foreground/60" />
              <p className="text-sm text-muted-foreground">
                {loading
                  ? 'Loading recent uploads…'
                  : dataError
                    ? 'Recent uploads are currently unavailable.'
                    : 'Your uploaded datasets will appear here.'}
              </p>
            </div>
          ) : (
            <div className="divide-y">
              {recent.map((file) => (
                <Link
                  key={file.id}
                  to={`/data?tab=${file.type === 'bim' ? 'bim' : file.type === 'simulation' ? 'simulations' : 'all'}`}
                  className="flex items-center gap-3 px-5 py-4 hover:bg-muted/50"
                >
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{file.filename}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {file.created_at
                        ? new Date(file.created_at).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })
                        : 'Date unavailable'}
                    </p>
                  </div>
                  <StatusBadge status={file.status} />
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </PageContainer>
  );
}
