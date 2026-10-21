import { Link } from 'react-router-dom';
import { ArrowRight, Blocks, Building2, Database, LineChart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageContainer } from '@/components/layout/PageContainer';

const workspaces = [
  {
    title: 'Building portfolio',
    description: 'Explore BIM models through a visual, building-first catalogue.',
    icon: Building2,
    href: '/buildings',
    action: 'Browse buildings',
  },
  {
    title: 'Data explorer',
    description: 'Review uploaded datasets and their current processing state.',
    icon: Database,
    href: '/data',
    action: 'Explore data',
  },
  {
    title: 'Components',
    description: 'A focused home for the systems and assets within each building.',
    icon: Blocks,
    href: '/components',
    action: 'View workspace',
  },
];

export default function OverviewPage() {
  return (
    <PageContainer size="wide" className="space-y-8 lg:space-y-10">
      <section className="relative overflow-hidden rounded-[2rem] bg-sidebar-background text-sidebar-foreground shadow-sm">
        <div className="relative z-10 grid min-h-[420px] gap-10 px-6 py-10 sm:px-10 sm:py-14 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-14">
          <div className="max-w-2xl">
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-sidebar-primary">
              Building intelligence, clearly connected
            </p>
            <h1 className="text-4xl font-semibold leading-[1.08] tracking-[-0.045em] sm:text-5xl lg:text-6xl">
              A clearer view of every building.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-sidebar-muted sm:text-lg">
              Navigate BIM models, operational data and simulation workflows from one
              coherent workspace.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button
                asChild
                size="lg"
                className="bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
              >
                <Link to="/buildings">
                  Explore buildings <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
              >
                <Link to="/data">Open data explorer</Link>
              </Button>
            </div>
          </div>

          <div className="relative mx-auto h-72 w-full max-w-lg" aria-hidden="true">
            <div className="absolute inset-6 rounded-[2rem] border border-sidebar-border bg-sidebar-accent/50" />
            <div className="absolute bottom-4 left-2 h-44 w-44 rounded-3xl border border-sidebar-border bg-sidebar-background/80 shadow-2xl sm:h-52 sm:w-52" />
            <div className="absolute right-2 top-2 h-56 w-48 rounded-3xl border border-sidebar-border bg-sidebar-accent shadow-2xl sm:w-60">
              <div className="grid h-full grid-cols-3 gap-3 p-6">
                {Array.from({ length: 9 }).map((_, index) => (
                  <span
                    key={index}
                    className="rounded-lg border border-sidebar-border bg-sidebar-primary/20"
                  />
                ))}
              </div>
            </div>
            <div className="absolute bottom-9 left-10 flex h-16 w-16 items-center justify-center rounded-2xl bg-sidebar-primary text-sidebar-primary-foreground shadow-xl">
              <Building2 className="h-8 w-8" />
            </div>
            <div className="absolute bottom-2 right-12 flex items-center gap-2 rounded-full border border-sidebar-border bg-sidebar-background px-4 py-2 text-xs text-sidebar-muted shadow-xl">
              <LineChart className="h-4 w-4 text-sidebar-primary" /> Connected insights
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              Workspace
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
              Start where your work lives
            </h2>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {workspaces.map((workspace) => (
            <Link
              key={workspace.title}
              to={workspace.href}
              className="group rounded-2xl border bg-card p-6 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
            >
              <div className="mb-10 flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                <workspace.icon className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold">{workspace.title}</h3>
              <p className="mt-2 min-h-12 text-sm leading-6 text-muted-foreground">
                {workspace.description}
              </p>
              <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-primary">
                {workspace.action}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
          ))}
        </div>
      </section>
    </PageContainer>
  );
}
