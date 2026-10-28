import { useEffect, useState } from 'react';
import { getBimFileByDataset, listBimFiles } from '@/api/bim_files';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import type { BimFileDto } from '@/types/api/bim';
import { BIMDetailsDialog } from './components/BIMDetailsDialog';
import { BimUploadDialog } from './components/BimUploadDialog';
import { BuildingCard } from './components/BuildingCard';
import { BuildingImageDialog } from './components/BuildingImageDialog';
import { SearchInput } from '@/components/ui/search-input';
import { ErrorNotice } from '@/components/layout/Feedback';

type BuildingSectionProps = {
  title: string;
  description: string;
  files: BimFileDto[];
  onDetails: (file: BimFileDto) => void;
  onEditImage: (file: BimFileDto) => void;
};

function BuildingSection({
  title,
  description,
  files,
  onDetails,
  onEditImage,
}: BuildingSectionProps) {
  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
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
              onEditImage={() => onEditImage(file)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed bg-card/50 px-6 py-8 text-sm text-muted-foreground">
          No models to display in this category.
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
  const [imageFile, setImageFile] = useState<BimFileDto | null>(null);
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('newest');
  const [retry, setRetry] = useState(0);
  const { resolvedRows, clearResolvedRows, queueDatasetId } = usePendingDatasetPolling({
    fetchByDatasetId: getBimFileByDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.dataset_id,
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
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
  }, [retry]);

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

  const visible = files
    .filter((file) => file.filename.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) =>
      sort === 'name'
        ? a.filename.localeCompare(b.filename)
        : new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime(),
    );
  const archetypes = visible.filter((file) => file.category === 'archetype');
  const pilots = visible.filter((file) => file.category !== 'archetype');

  const replaceFile = (updated: BimFileDto) => {
    setFiles((current) =>
      current.map((file) => (file.id === updated.id ? updated : file)),
    );
  };

  return (
    <PageContainer size="wide" className="space-y-7">
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

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search building models…"
        />
        <select
          aria-label="Sort building models"
          value={sort}
          onChange={(event) => setSort(event.target.value)}
          className="field sm:w-44"
        >
          <option value="newest">Newest first</option>
          <option value="name">Name A–Z</option>
        </select>
      </div>
      {error && (
        <ErrorNotice message={error} onRetry={() => setRetry((value) => value + 1)} />
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
        <div className="space-y-9">
          <BuildingSection
            title="Building Archetypes"
            description="Digital reference models for design, renovation and performance studies."
            files={archetypes}
            onDetails={setSelectedFile}
            onEditImage={setImageFile}
          />
          <BuildingSection
            title="Living Labs & Pilots"
            description="Physical demonstration sites for validating Le’Colaz solutions."
            files={pilots}
            onDetails={setSelectedFile}
            onEditImage={setImageFile}
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
      {imageFile && (
        <BuildingImageDialog
          building={imageFile}
          onClose={() => setImageFile(null)}
          onSaved={(updated) => {
            replaceFile(updated);
            setImageFile(null);
          }}
        />
      )}
    </PageContainer>
  );
}
