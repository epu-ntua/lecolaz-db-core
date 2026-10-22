import { useEffect, useState } from 'react';
import { ArrowLeft, Download } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { getBimFile, listBimSpaces } from '@/api/bim_files';
import { getDatasetDownloadUrl } from '@/api/datasets';
import { listSimulationFiles } from '@/api/simulation_files';
import { PageContainer } from '@/components/layout/PageContainer';
import { StatusBadge } from '@/components/ui/status-badge';
import { SearchInput } from '@/components/ui/search-input';
import { ErrorNotice, LoadingState } from '@/components/layout/Feedback';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useSimulationVariables } from '@/hooks/useSimulationVariables';
import { SimulationVariableChartDialog } from './components/SimulationVariableChartDialog';
import type { BimFileDto, BimSpaceDto } from '@/types/api/bim';
import type { SimulationFileDto, SimulationVariableDto } from '@/types/api/simulations';

export default function SimulationDetailsPage() {
  const { id } = useParams();
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [file, setFile] = useState<SimulationFileDto | null>(null);
  const [linkedBim, setLinkedBim] = useState<BimFileDto | null>(null);
  const [spaces, setSpaces] = useState<BimSpaceDto[]>([]);
  const [selectedVariable, setSelectedVariable] = useState<SimulationVariableDto | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const {
    variables,
    loading: variablesLoading,
    error: variablesError,
  } = useSimulationVariables(id ?? '');

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    listSimulationFiles()
      .then((rows) => {
        if (!cancelled) setFile(rows.find((row) => row.id === id) ?? null);
      })
      .catch(() => {
        if (!cancelled) setError('Simulation could not be loaded.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id, retry]);

  useEffect(() => {
    if (!file?.bim_dataset_id) {
      setLinkedBim(null);
      setSpaces([]);
      return;
    }
    getBimFile(file.bim_dataset_id)
      .then((bim) => {
        setLinkedBim(bim);
        return listBimSpaces(bim.id);
      })
      .then(setSpaces)
      .catch(() => {
        setLinkedBim(null);
        setSpaces([]);
      });
  }, [file?.bim_dataset_id]);

  if (loading)
    return (
      <PageContainer>
        <LoadingState label="Loading simulation…" />
      </PageContainer>
    );
  if (error)
    return (
      <PageContainer>
        <ErrorNotice message={error} onRetry={() => setRetry((value) => value + 1)} />
      </PageContainer>
    );
  if (!file)
    return (
      <PageContainer>
        <p className="mb-4 text-sm text-muted-foreground">Simulation not found.</p>
        <Button asChild variant="outline">
          <Link to="/data?tab=simulations">Back to simulations</Link>
        </Button>
      </PageContainer>
    );

  const spaceNames = new Map(
    spaces.map((space) => [space.id, space.name ?? space.global_id]),
  );
  const visibleVariables = variables.filter((variable) =>
    [
      variable.variable_name,
      variable.unit,
      variable.key,
      variable.bim_space_id ? spaceNames.get(variable.bim_space_id) : '',
    ].some((value) => value?.toLowerCase().includes(query.toLowerCase())),
  );

  return (
    <PageContainer size="wide" className="space-y-8">
      <div>
        <Button asChild variant="ghost" className="mb-4 -ml-3">
          <Link to="/data?tab=simulations">
            <ArrowLeft className="h-4 w-4" />
            Back to Simulation Datasets
          </Link>
        </Button>
        <div className="flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              Simulation dataset
            </p>
            <h1 className="mt-2 break-all text-2xl font-semibold tracking-tight">
              {file.filename}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Inspect processed metadata, variables and time-series results.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={file.status} />
            <Button asChild variant="outline">
              <a href={getDatasetDownloadUrl(file.dataset_id)} download>
                <Download className="h-4 w-4" />
                Download
              </a>
            </Button>
          </div>
        </div>
      </div>
      <section className="grid gap-4 sm:grid-cols-3">
        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase text-muted-foreground">
              Variables
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold">
            {typeof file.metadata?.variable_count === 'number'
              ? file.metadata.variable_count
              : '—'}
          </CardContent>
        </Card>
        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase text-muted-foreground">
              Timesteps
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold">
            {typeof file.metadata?.timestep_count === 'number'
              ? file.metadata.timestep_count
              : '—'}
          </CardContent>
        </Card>
        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase text-muted-foreground">
              Associated BIM
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm font-semibold">
            {linkedBim ? (
              <Link
                className="text-primary hover:underline"
                to={`/buildings/${linkedBim.id}`}
              >
                {linkedBim.filename}
              </Link>
            ) : file.bim_dataset_id ? (
              'Linked BIM unavailable'
            ) : (
              'Standalone simulation'
            )}
          </CardContent>
        </Card>
      </section>
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Simulation Variables</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Select a variable to open its full time-series chart.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <SearchInput
            value={query}
            onChange={setQuery}
            placeholder="Search variable, unit or space…"
          />
          <span className="text-xs text-muted-foreground">
            {variables.length} available variables
          </span>
        </div>
        <div className="overflow-hidden rounded-xl border bg-card">
          <div className="overflow-x-auto">
            <Table className="min-w-[720px]">
              <TableHeader className="bg-muted/50">
                <TableRow>
                  <TableHead>Variable</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead>Frequency</TableHead>
                  <TableHead>Space / Key</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleVariables.map((variable) => (
                  <TableRow key={variable.id} className="h-14">
                    <TableCell>
                      <Button
                        variant="link"
                        className="h-auto whitespace-normal p-0 text-left"
                        onClick={() => setSelectedVariable(variable)}
                      >
                        {variable.variable_name}
                      </Button>
                    </TableCell>
                    <TableCell>{variable.unit ?? '—'}</TableCell>
                    <TableCell>{variable.frequency ?? '—'}</TableCell>
                    <TableCell>
                      {variable.bim_space_id
                        ? (spaceNames.get(variable.bim_space_id) ?? variable.key ?? '—')
                        : (variable.key ?? '—')}
                    </TableCell>
                  </TableRow>
                ))}
                {variablesLoading && (
                  <TableRow>
                    <TableCell
                      colSpan={4}
                      className="h-24 text-center text-muted-foreground"
                    >
                      Loading variables…
                    </TableCell>
                  </TableRow>
                )}
                {variablesError && (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-destructive">
                      {variablesError}
                    </TableCell>
                  </TableRow>
                )}
                {!variablesLoading &&
                  !variablesError &&
                  visibleVariables.length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={4}
                        className="h-24 text-center text-muted-foreground"
                      >
                        {variables.length
                          ? 'No variables match your search.'
                          : 'No variables found.'}
                      </TableCell>
                    </TableRow>
                  )}
              </TableBody>
            </Table>
          </div>
        </div>
      </section>
      {selectedVariable && (
        <SimulationVariableChartDialog
          simulationId={file.id}
          variable={selectedVariable}
          onClose={() => setSelectedVariable(null)}
        />
      )}
    </PageContainer>
  );
}
