import { useEffect, useMemo, useState } from 'react';
import { Download, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getDatasetDownloadUrl } from '@/api/datasets';
import {
  fetchBimMetadata,
  listBimSpaces,
  listBimSimulations,
  listBimStoreys,
} from '@/api/bim_files';
import { uploadSimulationFile } from '@/api/simulation_files';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { FileUpload } from '@/pages/DataDiscovery/components/FileUpload';
import { SimulationDetailsModal } from '@/pages/Simulations/components/SimulationDetailsModal';
import type { BimFileDto, BimMetadataDto, BimSpaceDto, BimStoreyDto } from '@/types/api/bim';
import type { SimulationFileDto } from '@/types/api/simulations';

function getStatusVariant(status: string | null) {
  if (status === 'failed') {
    return 'destructive' as const;
  }

  if (status === 'processed') {
    return 'default' as const;
  }

  return 'secondary' as const;
}

export function BIMDetailsDialog({
  file,
  onClose,
}: {
  file: BimFileDto;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const [metadata, setMetadata] = useState<BimMetadataDto | null>(null);
  const [storeys, setStoreys] = useState<BimStoreyDto[]>([]);
  const [spaces, setSpaces] = useState<BimSpaceDto[]>([]);
  const [simulations, setSimulations] = useState<SimulationFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [selectedSimulation, setSelectedSimulation] = useState<SimulationFileDto | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchBimMetadata(file.id),
      listBimStoreys(file.id),
      listBimSpaces(file.id),
      listBimSimulations(file.id),
    ])
      .then(([nextMetadata, nextStoreys, nextSpaces, nextSimulations]) => {
        if (cancelled) {
          return;
        }
        setUploadMessage(null);
        setMetadata(nextMetadata);
        setStoreys(nextStoreys);
        setSpaces(nextSpaces);
        setSimulations(nextSimulations);
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load BIM details');
          setMetadata(null);
          setStoreys([]);
          setSpaces([]);
          setSimulations([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [file.id]);

  const storeyNameById = useMemo(
    () =>
      new Map(
        storeys.map((storey) => [storey.id, storey.name ?? storey.global_id] as const),
      ),
    [storeys],
  );

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-6xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <div className="flex items-start justify-between gap-4 pr-8">
            <div className="space-y-2">
              <DialogTitle className="text-xl">{file.filename}</DialogTitle>
              <DialogDescription>BIM dataset details and extracted structure</DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={getStatusVariant(file.status)} className="capitalize">
                {file.status ?? '--'}
              </Badge>
              <Button asChild variant="outline" size="sm">
                <a href={getDatasetDownloadUrl(file.dataset_id)} download>
                  <Download />
                  Download
                </a>
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={() => navigate(`/bim/${file.id}`)}
              >
                <Eye />
                View
              </Button>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 overflow-y-auto px-6 py-5">
          <section className="grid gap-4 md:grid-cols-3">
            <Card className="shadow-none">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  Schema
                </CardTitle>
              </CardHeader>
              <CardContent className="text-lg font-semibold">
                {file.schema ?? '--'}
              </CardContent>
            </Card>
            <Card className="shadow-none">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  Storeys
                </CardTitle>
              </CardHeader>
              <CardContent className="text-lg font-semibold">
                {typeof file.stats?.storeys === 'number' ? file.stats.storeys : storeys.length}
              </CardContent>
            </Card>
            <Card className="shadow-none">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  Spaces
                </CardTitle>
              </CardHeader>
              <CardContent className="text-lg font-semibold">
                {typeof file.stats?.spaces === 'number' ? file.stats.spaces : spaces.length}
              </CardContent>
            </Card>
          </section>

          {error && (
            <section className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </section>
          )}

          <Card className="shadow-none">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-medium">File Metadata</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <div className="text-sm">
                <div className="text-muted-foreground">Filename</div>
                <div>{metadata?.filename ?? file.filename}</div>
              </div>
              <div className="text-sm">
                <div className="text-muted-foreground">Content Type</div>
                <div>{metadata?.content_type ?? '--'}</div>
              </div>
              <div className="text-sm">
                <div className="text-muted-foreground">Uploaded</div>
                <div>
                  {metadata?.upload_date
                    ? new Date(metadata.upload_date).toLocaleString()
                    : '--'}
                </div>
              </div>
              <div className="text-sm">
                <div className="text-muted-foreground">Size</div>
                <div>
                  {typeof metadata?.size === 'number'
                    ? `${metadata.size.toLocaleString()} bytes`
                    : '--'}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-none">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-medium">
                Simulations for {file.filename}
              </CardTitle>
              <DialogDescription className="text-left">
                Linked simulations are scoped to this BIM. New uploads from here will be
                matched against these spaces by global id when possible.
              </DialogDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {simulations.length === 0 ? (
                <div className="text-sm text-muted-foreground">No linked simulations yet.</div>
              ) : (
                <div className="rounded-md border border-border bg-card">
                  <Table className="min-w-[640px] text-sm text-foreground">
                    <TableHeader className="border-b border-border bg-muted">
                      <TableRow className="text-left hover:bg-transparent">
                        <TableHead className="px-3 py-2 font-medium text-muted-foreground">
                          Filename
                        </TableHead>
                        <TableHead className="px-3 py-2 font-medium text-muted-foreground">
                          Status
                        </TableHead>
                        <TableHead className="px-3 py-2 font-medium text-muted-foreground">
                          Processed
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {simulations.map((simulation) => (
                        <TableRow key={simulation.id} className="align-top">
                          <TableCell className="px-3 py-2">
                            <Button
                              type="button"
                              variant="link"
                              className="h-auto p-0"
                              onClick={() => setSelectedSimulation(simulation)}
                            >
                              {simulation.filename}
                            </Button>
                          </TableCell>
                          <TableCell className="px-3 py-2">
                            <Badge
                              variant={getStatusVariant(simulation.status)}
                              className="capitalize"
                            >
                              {simulation.status ?? '--'}
                            </Badge>
                          </TableCell>
                          <TableCell className="px-3 py-2 text-muted-foreground">
                            {typeof simulation.metadata?.processed_at === 'string'
                              ? new Date(simulation.metadata.processed_at).toLocaleString()
                              : '--'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              <FileUpload
                onUploaded={async () => {
                  setUploadMessage('Simulation uploaded and queued for processing.');
                  const nextSimulations = await listBimSimulations(file.id);
                  setSimulations(nextSimulations);
                }}
                uploadAction={(uploadedFile) => uploadSimulationFile(uploadedFile, file.id)}
                accept=".eso"
                buttonLabel="Upload Another Simulation"
                uploadingLabel="Uploading simulation..."
                errorMessage="BIM-scoped simulation upload failed"
              />
              {uploadMessage && (
                <div className="text-sm text-muted-foreground">{uploadMessage}</div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-none">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-medium">Storeys</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-sm text-muted-foreground">Loading storeys...</div>
              ) : storeys.length === 0 ? (
                <div className="text-sm text-muted-foreground">No storeys found</div>
              ) : (
                <div className="max-h-64 overflow-auto rounded-md border border-border bg-card">
                  <Table className="min-w-[640px] text-sm text-foreground">
                    <TableHeader className="border-b border-border bg-muted">
                      <TableRow className="text-left hover:bg-transparent">
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Name
                        </TableHead>
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Elevation
                        </TableHead>
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Global ID
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {storeys.map((storey) => (
                        <TableRow key={storey.id} className="align-top">
                          <TableCell className="px-3 py-2">
                            {storey.name ?? '--'}
                          </TableCell>
                          <TableCell className="px-3 py-2 text-muted-foreground">
                            {storey.elevation ?? '--'}
                          </TableCell>
                          <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                            {storey.global_id}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-none">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-medium">Spaces</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-sm text-muted-foreground">Loading spaces...</div>
              ) : spaces.length === 0 ? (
                <div className="text-sm text-muted-foreground">No spaces found</div>
              ) : (
                <div className="max-h-72 overflow-auto rounded-md border border-border bg-card">
                  <Table className="min-w-[860px] text-sm text-foreground">
                    <TableHeader className="border-b border-border bg-muted">
                      <TableRow className="text-left hover:bg-transparent">
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Name
                        </TableHead>
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Global ID
                        </TableHead>
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Storey
                        </TableHead>
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Area
                        </TableHead>
                        <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                          Volume
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {spaces.map((space) => (
                        <TableRow key={space.id} className="align-top">
                          <TableCell className="px-3 py-2">{space.name ?? '--'}</TableCell>
                          <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                            {space.global_id}
                          </TableCell>
                          <TableCell className="px-3 py-2 text-muted-foreground">
                            {space.storey_id
                              ? (storeyNameById.get(space.storey_id) ?? space.storey_id)
                              : '--'}
                          </TableCell>
                          <TableCell className="px-3 py-2 text-muted-foreground">
                            {space.area ?? '--'}
                          </TableCell>
                          <TableCell className="px-3 py-2 text-muted-foreground">
                            {space.volume ?? '--'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </DialogContent>
      {selectedSimulation && (
        <SimulationDetailsModal
          file={selectedSimulation}
          onClose={() => setSelectedSimulation(null)}
        />
      )}
    </Dialog>
  );
}
