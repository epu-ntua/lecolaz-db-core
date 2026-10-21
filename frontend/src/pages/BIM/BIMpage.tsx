import { useEffect, useState } from 'react';
import { getBimFileByDataset, listBimFiles } from '@/api/bim_files';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import type { BimFileDto } from '@/types/api/bim';
import { BIMDetailsDialog } from './components/BIMDetailsDialog';
import { BimUploadDialog } from './components/BimUploadDialog';
import { BuildingCard } from './components/BuildingCard';

type BuildingSectionProps = {
  title: string;
  description: string;
  files: BimFileDto[];
  onDetails: (file: BimFileDto) => void;
};

function BuildingSection({ title, description, files, onDetails }: BuildingSectionProps) {
  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {files.length} {files.length === 1 ? 'model' : 'models'}
        </span>
      </div>
      <div className="h-px bg-border" />
      {files.length > 0 ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {files.map((file) => (
            <BuildingCard
              key={file.id}
              building={file}
              onDetails={() => onDetails(file)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed bg-card/50 px-6 py-8 text-sm text-muted-foreground">
          No models in this category yet.
        </div>
      )}
    </section>
  );
}

export default function BIMPage() {
  const [files, setFiles] = useState<BimFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<BimFileDto | null>(null);
  const { resolvedRows, clearResolvedRows, queueDatasetId } = usePendingDatasetPolling({
    fetchByDatasetId: getBimFileByDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.dataset_id,
  });

  useEffect(() => {
    let cancelled = false;
    listBimFiles()
      .then((rows) => {
        if (!cancelled) setFiles(rows);
      })
      .catch(() => {
        if (!cancelled) setError('Buildings could not be loaded. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (resolvedRows.length === 0) return;
    setFiles((current) => {
      const next = [...current];
      resolvedRows.forEach((bim) => {
        const index = next.findIndex((row) => row.dataset_id === bim.dataset_id);
        if (index >= 0) next[index] = bim;
      });
      return next;
    });
    clearResolvedRows();
  }, [clearResolvedRows, resolvedRows]);

  const archetypes = files.filter((file) => file.category === 'archetype');
  const pilots = files.filter((file) => file.category !== 'archetype');

  const replaceFile = (updated: BimFileDto) => {
    setFiles((current) =>
      current.map((file) => (file.id === updated.id ? updated : file)),
    );
  };

  return (
    <PageContainer size="wide" className="space-y-10">
      <PageHeader
        eyebrow="Portfolio"
        title="Buildings & Pilots"
        description="Explore your building models, open the BIM viewer and manage the source files behind each digital asset."
        actions={
          <BimUploadDialog
            onUploaded={async (result) => {
              const bim = await getBimFileByDataset(result.dataset_id);
              setFiles((current) => [bim, ...current.filter((row) => row.id !== bim.id)]);
              queueDatasetId(result.dataset_id);
            }}
          />
        }
      />

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="aspect-[4/3] animate-pulse rounded-2xl border bg-muted"
            />
          ))}
        </div>
      ) : (
        <div className="space-y-12">
          <BuildingSection
            title="Building Archetypes"
            description="Digital reference models for design, renovation and performance studies."
            files={archetypes}
            onDetails={setSelectedFile}
          />
          <BuildingSection
            title="Living Labs & Pilots"
            description="Physical demonstration sites for validating Le’Colaz solutions."
            files={pilots}
            onDetails={setSelectedFile}
          />
        </div>
      )}

      {selectedFile && (
        <BIMDetailsDialog
          file={selectedFile}
          onCategoryChanged={(updated) => {
            replaceFile(updated);
            setSelectedFile(updated);
          }}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </PageContainer>
  );
}
