import { Link } from 'react-router-dom';
import { ArrowRight, FileBarChart } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';

export default function ScenariosPage() {
  return (
    <PageContainer className="space-y-8">
      <PageHeader
        title="Scenarios & Insights"
        description="Explore building configurations, simulation scenarios and performance assessments."
      />
      <section className="flex min-h-[360px] flex-col items-center justify-center rounded-2xl border border-dashed bg-card/70 px-6 py-14 text-center">
        <div className="mb-5 rounded-2xl bg-accent p-4 text-accent-foreground">
          <FileBarChart className="h-7 w-7" />
        </div>
        <h2 className="text-xl font-semibold">
          Scenario-based analysis is under development.
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
          This area will bring together building configurations, simulation results and
          performance comparisons as the corresponding workflows are defined.
        </p>
        <Link
          to="/data?tab=simulations"
          className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
        >
          Explore simulation datasets <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </PageContainer>
  );
}
