import { useEffect, useState } from 'react';
import * as Reactodia from '@reactodia/workspace';
import { RefreshCw } from 'lucide-react';
import { getInitialOntologyInstances, ONTOLOGY_QUERY_URL } from '@/api/ontology';
import { ErrorNotice, LoadingState } from '@/components/layout/Feedback';
import { Button } from '@/components/ui/button';

const Layouts = Reactodia.defineLayoutWorker(
  () =>
    new Worker(new URL('@reactodia/workspace/layout.worker', import.meta.url), {
      type: 'module',
    }),
);

export default function OntologyExplorer() {
  const [revision, setRevision] = useState(0);

  return (
    <section className="space-y-4" aria-label="Ontology explorer">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Ontology Explorer</h2>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Start with building, component, simulation run and energy model dataset
            instances. Search for more entities or select an instance to explore its
            connections across all datasets.
          </p>
        </div>
        <Button variant="outline" onClick={() => setRevision((value) => value + 1)}>
          <RefreshCw className="h-4 w-4" /> Reload graph
        </Button>
      </div>
      <OntologyWorkspace
        key={revision}
        onRetry={() => setRevision((value) => value + 1)}
      />
    </section>
  );
}

function OntologyWorkspace({ onRetry }: { onRetry: () => void }) {
  const { defaultLayout } = Reactodia.useWorker(Layouts);
  const [workspace] = useState(() => Reactodia.createWorkspace({ defaultLayout }));
  const [loading, setLoading] = useState(true);
  const [empty, setEmpty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const { model, performLayout } = workspace;
    async function load() {
      // Allow React to finish mounting the canvas, including StrictMode's probe.
      await Promise.resolve();
      if (signal.aborted) return;
      try {
        const dataProvider = new Reactodia.SparqlDataProvider(
          {
            endpointUrl: ONTOLOGY_QUERY_URL,
            queryMethod: 'POST',
            chunk: { maxSize: 100, unit: 'itemCount' },
            queryFunction: ({ url, signal: requestSignal, ...options }) =>
              fetch(url, {
                ...options,
                cache: 'no-store',
                signal: requestSignal ? AbortSignal.any([signal, requestSignal]) : signal,
              }),
          },
          {
            ...Reactodia.OwlStatsSettings,
            // Dataset titles are published as dct:title rather than rdfs:label.
            dataLabelProperty: '(rdfs:label|<http://purl.org/dc/terms/title>)',
          },
        );
        await model.createNewDiagram({ dataProvider, signal });
        const iris = await getInitialOntologyInstances(signal);
        signal.throwIfAborted();
        for (const iri of iris) model.createElement(iri as Reactodia.ElementIri);
        await model.requestData();
        signal.throwIfAborted();
        await performLayout({ signal });
        signal.throwIfAborted();
        model.history.reset();
        setEmpty(iris.length === 0);
      } catch (cause) {
        if (!signal.aborted) {
          setError(
            cause instanceof Error
              ? cause.message
              : 'The knowledge graph could not be loaded.',
          );
        }
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    }
    void load();
    // WorkspaceProvider disposes its view; all provider requests share this
    // signal. Avoid discardLayout here: Reactodia 0.35 schedules a viewport
    // update after its canvas has already unmounted.
    return () => controller.abort();
  }, [workspace]);

  return (
    <div className="space-y-3">
      {error && <ErrorNotice message={error} onRetry={onRetry} />}
      {empty && !error && (
        <p
          role="status"
          className="rounded-xl border bg-card p-4 text-sm text-muted-foreground"
        >
          No building, component, simulation run or energy model dataset instances are
          available in the knowledge graph yet. You can still search and explore other
          published data.
        </p>
      )}
      <div className="relative h-[70vh] min-h-[480px] overflow-hidden rounded-xl border bg-card">
        <Reactodia.WorkspaceProvider workspace={workspace}>
          <Reactodia.DefaultWorkspace
            colorScheme="light"
            annotations={null}
            menu={null}
          />
        </Reactodia.WorkspaceProvider>
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/90">
            <LoadingState label="Loading knowledge graph…" />
          </div>
        )}
      </div>
    </div>
  );
}
