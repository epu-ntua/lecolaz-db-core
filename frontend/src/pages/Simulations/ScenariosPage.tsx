import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ChartNoAxesCombined,
  Building2,
  Files,
  CircleCheck,
} from 'lucide-react';
import { listSimulationFiles } from '@/api/simulation_files';
import { listBimFiles } from '@/api/bim_files';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { MetricCard } from '@/components/layout/MetricCard';
import { ErrorNotice } from '@/components/layout/Feedback';
import { Button } from '@/components/ui/button';
import { SearchInput } from '@/components/ui/search-input';
import { SimulationsFilesTable } from './components/SimulationsFilesTable';
import type { SimulationFileDto } from '@/types/api/simulations';
import type { BimFileDto } from '@/types/api/bim';

export default function ScenariosPage() {
  const [files, setFiles] = useState<SimulationFileDto[]>([]);
  const [bims, setBims] = useState<BimFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [query, setQuery] = useState('');
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    Promise.allSettled([listSimulationFiles(), listBimFiles()]).then(
      ([simulations, buildings]) => {
        if (cancelled) return;
        if (simulations.status === 'fulfilled') setFiles(simulations.value);
        else setError(true);
        if (buildings.status === 'fulfilled') setBims(buildings.value);
        setLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [retry]);
  return (
    <PageContainer size="wide" className="space-y-7">
      <PageHeader
        eyebrow="Analysis workspace"
        title="Scenarios & Insights"
        description="Explore simulation outputs and the building models behind them."
        actions={
          <Button asChild size="lg">
            <Link to="/data?tab=simulations">
              Manage simulations <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        }
      />
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        <MetricCard
          label="Simulation outputs"
          value={loading || error ? '—' : files.length}
          detail="Imported output files"
          icon={Files}
        />
        <MetricCard
          label="Processed"
          value={
            loading || error
              ? '—'
              : files.filter((file) => file.status === 'processed').length
          }
          detail="Outputs ready for inspection"
          icon={CircleCheck}
        />
        <MetricCard
          label="Linked buildings"
          value={
            loading || error
              ? '—'
              : new Set(files.map((file) => file.bim_dataset_id).filter(Boolean)).size
          }
          detail="BIM models with simulations"
          icon={Building2}
        />
      </div>
      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Explore results</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Open an output to inspect its variables and time-series charts.
            </p>
          </div>
          <SearchInput
            value={query}
            onChange={setQuery}
            placeholder="Search simulation outputs…"
          />
        </div>
        {error ? (
          <ErrorNotice
            message="Simulation outputs could not be loaded."
            onRetry={() => setRetry((value) => value + 1)}
          />
        ) : (
          <SimulationsFilesTable
            files={files.filter((file) =>
              file.filename.toLowerCase().includes(query.toLowerCase()),
            )}
            bims={bims}
            loading={loading}
          />
        )}
      </section>
      <aside className="flex items-start gap-4 rounded-xl border bg-muted/50 p-5">
        <ChartNoAxesCombined className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
        <div>
          <h2 className="text-sm font-medium">
            Scenario comparison is under development
          </h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Individual simulation results are available above. Creating and comparing
            scenarios is not yet supported.
          </p>
        </div>
      </aside>
    </PageContainer>
  );
}
