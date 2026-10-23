import { useEffect, useState } from 'react';
import { Blocks } from 'lucide-react';
import { listComponents } from '@/api/components';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorNotice } from '@/components/layout/Feedback';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { SearchInput } from '@/components/ui/search-input';
import { COMPONENT_CLASS_LABELS } from '@/lib/constants';
import type { ComponentClass, ModularComponentDto } from '@/types/api/components';
import { ComponentCard } from './components/ComponentCard';
import { ComponentDetailsDialog } from './components/ComponentDetailsDialog';

export default function ComponentsPage() {
  const [components, setComponents] = useState<ModularComponentDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ModularComponentDto | null>(null);
  const [query, setQuery] = useState('');
  const [componentClass, setComponentClass] = useState<ComponentClass | 'all'>('all');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listComponents()
      .then((rows) => {
        if (!cancelled) setComponents(rows);
      })
      .catch(() => {
        if (!cancelled) setError('Components could not be loaded. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [retry]);

  const visible = components
    .filter(
      (component) =>
        componentClass === 'all' || component.component_class === componentClass,
    )
    .filter((component) => component.name.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <PageContainer size="wide" className="space-y-7">
      <PageHeader
        eyebrow="Workspace"
        title="Components"
        description="Browse the modular components and their digital product passports."
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput value={query} onChange={setQuery} placeholder="Search components…" />
        <select
          aria-label="Filter by component class"
          value={componentClass}
          onChange={(event) =>
            setComponentClass(event.target.value as ComponentClass | 'all')
          }
          className="field sm:w-48"
        >
          <option value="all">All classes</option>
          {Object.entries(COMPONENT_CLASS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {error && (
        <ErrorNotice message={error} onRetry={() => setRetry((value) => value + 1)} />
      )}

      {loading ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="aspect-[4/3] animate-pulse rounded-2xl border bg-muted"
            />
          ))}
        </div>
      ) : visible.length > 0 ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((component) => (
            <ComponentCard
              key={component.id}
              component={component}
              onDetails={() => setSelected(component)}
            />
          ))}
        </div>
      ) : (
        !error && (
          <EmptyState
            icon={Blocks}
            title="No components to display"
            description={
              components.length > 0
                ? 'No components match the current search or filter.'
                : 'No modular components have been added yet.'
            }
          />
        )
      )}

      {selected && (
        <ComponentDetailsDialog component={selected} onClose={() => setSelected(null)} />
      )}
    </PageContainer>
  );
}
