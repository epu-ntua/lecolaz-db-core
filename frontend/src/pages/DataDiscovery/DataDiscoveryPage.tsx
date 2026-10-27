import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getBimFileByDataset, listBimFiles } from '@/api/bim_files';
import { getDataset, listDatasets } from '@/api/datasets';
import { getSimulationFileByDataset, listSimulationFiles } from '@/api/simulation_files';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { SearchInput } from '@/components/ui/search-input';
import { ErrorNotice } from '@/components/layout/Feedback';
import { cn } from '@/lib/utils';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import { BimUploadDialog } from '@/pages/BIM/components/BimUploadDialog';
import { BimDatasetsTable } from './components/BimDatasetsTable';
import { FilesTable } from './components/FilesTable';
import { GenericUploadDialog } from './components/GenericUploadDialog';
import { SimulationUploadDialog } from './components/SimulationUploadDialog';
import { SimulationsFilesTable } from '@/pages/Simulations/components/SimulationsFilesTable';
import type { BimFileDto } from '@/types/api/bim';
import type { DatasetDto } from '@/types/api/datasets';
import type { SimulationFileDto } from '@/types/api/simulations';

const tabs = [
  { value: 'all', label: 'All Datasets' },
  { value: 'simulations', label: 'Simulation Datasets' },
  { value: 'bim', label: 'BIM Datasets' },
] as const;

function SectionHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  );
}

export default function DataDiscoveryPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [retry, setRetry] = useState(0);
  const matches = (row: { filename: string; status?: string | null }) =>
    row.filename.toLowerCase().includes(query.toLowerCase()) &&
    (status === 'all' || row.status === status);
  const [params] = useSearchParams();
  const requestedTab = params.get('tab');
  const activeTab = tabs.some((tab) => tab.value === requestedTab)
    ? requestedTab!
    : 'all';
  const [datasets, setDatasets] = useState<DatasetDto[]>([]);
  const [simulations, setSimulations] = useState<SimulationFileDto[]>([]);
  const [bims, setBims] = useState<BimFileDto[]>([]);
  const [loading, setLoading] = useState({ all: true, simulations: true, bim: true });
  const [errors, setErrors] = useState({ all: false, simulations: false, bim: false });
  const {
    resolvedRows: resolvedDatasets,
    clearResolvedRows: clearResolvedDatasets,
    queueDatasetId: queueDataset,
  } = usePendingDatasetPolling({
    fetchByDatasetId: getDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.id,
  });
  const {
    resolvedRows: resolvedSimulations,
    clearResolvedRows: clearResolvedSimulations,
    queueDatasetId: queueSimulation,
  } = usePendingDatasetPolling({
    fetchByDatasetId: getSimulationFileByDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.dataset_id,
  });
  const {
    resolvedRows: resolvedBims,
    clearResolvedRows: clearResolvedBims,
    queueDatasetId: queueBim,
  } = usePendingDatasetPolling({
    fetchByDatasetId: getBimFileByDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.dataset_id,
  });

  useEffect(() => {
    setLoading({ all: true, simulations: true, bim: true });
    setErrors({ all: false, simulations: false, bim: false });
    listDatasets()
      .then(setDatasets)
      .catch(() => setErrors((state) => ({ ...state, all: true })))
      .finally(() => setLoading((state) => ({ ...state, all: false })));
    listSimulationFiles()
      .then(setSimulations)
      .catch(() => setErrors((state) => ({ ...state, simulations: true })))
      .finally(() => setLoading((state) => ({ ...state, simulations: false })));
    listBimFiles()
      .then(setBims)
      .catch(() => setErrors((state) => ({ ...state, bim: true })))
      .finally(() => setLoading((state) => ({ ...state, bim: false })));
  }, [retry]);

  useEffect(() => {
    if (!resolvedDatasets.length) return;
    setDatasets((current) =>
      current.map((row) => resolvedDatasets.find((next) => next.id === row.id) ?? row),
    );
    clearResolvedDatasets();
  }, [resolvedDatasets, clearResolvedDatasets]);

  useEffect(() => {
    if (!resolvedSimulations.length) return;
    setSimulations((current) =>
      current.map(
        (row) =>
          resolvedSimulations.find((next) => next.dataset_id === row.dataset_id) ?? row,
      ),
    );
    clearResolvedSimulations();
  }, [resolvedSimulations, clearResolvedSimulations]);

  useEffect(() => {
    if (!resolvedBims.length) return;
    setBims((current) =>
      current.map(
        (row) => resolvedBims.find((next) => next.dataset_id === row.dataset_id) ?? row,
      ),
    );
    clearResolvedBims();
  }, [resolvedBims, clearResolvedBims]);

  return (
    <PageContainer size="wide" className="space-y-6">
      <PageHeader
        eyebrow="Data workspace"
        title="Data Explorer"
        description="Browse, manage and explore datasets available in the Le’Colaz platform."
      />
      <nav
        aria-label="Dataset type"
        className="flex gap-5 overflow-x-auto overflow-y-hidden border-b"
      >
        {tabs.map((tab) => (
          <Link
            key={tab.value}
            to={`/data?tab=${tab.value}`}
            aria-current={activeTab === tab.value ? 'page' : undefined}
            onClick={() => {
              setQuery('');
              setStatus('all');
            }}
            className={cn(
              'relative whitespace-nowrap pb-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground',
              activeTab === tab.value &&
                'text-primary after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary',
            )}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search datasets by filename…"
        />
        <select
          className="field sm:w-44"
          aria-label="Filter by processing status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="processed">Processed</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      <div className="space-y-5 pt-0">
        {activeTab === 'all' && (
          <>
            <SectionHeader
              title="All Datasets"
              description="Review uploaded files and their processing status."
              action={
                <GenericUploadDialog
                  onUploaded={async (result) => {
                    const dataset = await getDataset(result.dataset_id);
                    setDatasets((current) => [
                      dataset,
                      ...current.filter((row) => row.id !== dataset.id),
                    ]);
                    queueDataset(result.dataset_id);
                  }}
                />
              }
            />
            {errors.all ? (
              <ErrorNotice
                message="Datasets could not be loaded."
                onRetry={() => setRetry((value) => value + 1)}
              />
            ) : (
              <FilesTable files={datasets.filter(matches)} loading={loading.all} />
            )}
          </>
        )}

        {activeTab === 'simulations' && (
          <>
            <SectionHeader
              title="Simulation Datasets"
              description="Manage imported simulation outputs and explore their available variables and results."
              action={
                <SimulationUploadDialog
                  onUploaded={async (result) => {
                    const simulation = await getSimulationFileByDataset(
                      result.dataset_id,
                    );
                    const dataset = await getDataset(result.dataset_id);
                    setSimulations((current) => [
                      simulation,
                      ...current.filter((row) => row.id !== simulation.id),
                    ]);
                    setDatasets((current) => [
                      dataset,
                      ...current.filter((row) => row.id !== dataset.id),
                    ]);
                    queueSimulation(result.dataset_id);
                  }}
                />
              }
            />
            {errors.simulations ? (
              <ErrorNotice
                message="Simulation datasets could not be loaded."
                onRetry={() => setRetry((value) => value + 1)}
              />
            ) : (
              <SimulationsFilesTable
                files={simulations.filter(matches)}
                bims={bims}
                loading={loading.simulations}
              />
            )}
          </>
        )}

        {activeTab === 'bim' && (
          <>
            <SectionHeader
              title="BIM Datasets"
              description="Access imported IFC models and their associated technical information."
              action={
                <BimUploadDialog
                  onUploaded={async (result) => {
                    const bim = await getBimFileByDataset(result.dataset_id);
                    const dataset = await getDataset(result.dataset_id);
                    setBims((current) => [
                      bim,
                      ...current.filter((row) => row.id !== bim.id),
                    ]);
                    setDatasets((current) => [
                      dataset,
                      ...current.filter((row) => row.id !== dataset.id),
                    ]);
                    queueBim(result.dataset_id);
                  }}
                />
              }
            />
            {errors.bim ? (
              <ErrorNotice
                message="BIM datasets could not be loaded."
                onRetry={() => setRetry((value) => value + 1)}
              />
            ) : (
              <BimDatasetsTable files={bims.filter(matches)} loading={loading.bim} />
            )}
          </>
        )}
      </div>
    </PageContainer>
  );
}
