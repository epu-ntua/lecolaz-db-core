import {
  ArrowUpRight,
  Container,
  Database,
  ExternalLink,
  Workflow,
  type LucideIcon,
} from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';

type InfrastructureService = {
  name: string;
  description: string;
  action: string;
  icon: LucideIcon;
  url?: string;
};

const services: InfrastructureService[] = [
  {
    name: 'MinIO Console',
    description: 'Browse and manage object storage, buckets and uploaded files.',
    action: 'Open Console',
    icon: Database,
    url: import.meta.env.VITE_MINIO_CONSOLE_URL,
  },
  {
    name: 'Dagster',
    description: 'Monitor data ingestion pipelines, execution runs and processing failures.',
    action: 'Open Dagster',
    icon: Workflow,
    url: import.meta.env.VITE_DAGSTER_URL,
  },
  {
    name: 'Portainer',
    description: 'Inspect Docker containers, logs and platform services.',
    action: 'Open Portainer',
    icon: Container,
    url: import.meta.env.VITE_PORTAINER_URL,
  },
];

function ServiceAction({ service }: { service: InfrastructureService }) {
  if (!service.url) {
    return <span className="text-sm font-medium text-muted-foreground">Not configured</span>;
  }

  return (
    <a
      href={service.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-colors hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      {service.action}
      <ArrowUpRight className="h-4 w-4" />
    </a>
  );
}

export default function AdministrationPage() {
  return (
    <PageContainer className="space-y-8">
      <PageHeader
        title="Administration"
        description="Access infrastructure services and platform management tools."
      />

      <section className="space-y-5">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Infrastructure Services</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground sm:text-base">
            External tools used to operate and maintain the platform.
          </p>
        </div>

        <div className="grid items-stretch gap-4 md:grid-cols-2 xl:grid-cols-3">
          {services.map((service) => {
            const Icon = service.icon;

            return (
              <article
                key={service.name}
                className="flex min-h-56 flex-col rounded-xl border bg-card p-5 text-card-foreground"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h3 className="font-semibold">{service.name}</h3>
                  </div>
                  <ExternalLink
                    className="mt-1 h-4 w-4 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                </div>

                <p className="mt-6 max-w-sm text-sm leading-6 text-muted-foreground">
                  {service.description}
                </p>

                <div className="mt-auto pt-8">
                  <ServiceAction service={service} />
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </PageContainer>
  );
}
