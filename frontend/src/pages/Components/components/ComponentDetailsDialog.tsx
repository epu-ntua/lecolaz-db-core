import { useEffect, useState, type ReactNode } from 'react';
import { Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getBimFile, listBimFiles } from '@/api/bim_files';
import { getComponentFileUrl, updateComponentBuilding } from '@/api/components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SearchInput } from '@/components/ui/search-input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
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
import { cn } from '@/lib/utils';
import { BIMDetailsDialog } from '@/pages/BIM/components/BIMDetailsDialog';
import { buildingName } from '@/lib/format';
import type { BimFileDto } from '@/types/api/bim';
import type { ModularComponentDto } from '@/types/api/components';
import { ComponentSensorsTab } from './ComponentSensorsTab';

const tabs = [
  { value: 'traceability', label: 'Traceability' },
  { value: 'transparency', label: 'Transparency' },
  { value: 'trust', label: 'Trust' },
  { value: 'building', label: 'Building' },
  { value: 'sensors', label: 'Sensors' },
] as const;

type TabValue = (typeof tabs)[number]['value'];

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="text-sm">
      <div className="text-muted-foreground">{label}</div>
      <div>{value ?? '--'}</div>
    </div>
  );
}

function Section({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <Card className="shadow-none">
      {title && (
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent
        className={cn('grid gap-3 break-words md:grid-cols-2', !title && 'pt-6')}
      >
        {children}
      </CardContent>
    </Card>
  );
}

const withUnit = (value: number | undefined, unit: string) =>
  typeof value === 'number' ? `${value} ${unit}` : undefined;

export function ComponentDetailsDialog({
  component,
  onClose,
  onUpdated,
}: {
  component: ModularComponentDto;
  onClose: () => void;
  onUpdated: (component: ModularComponentDto) => void;
}) {
  const dpp = component.dpp;
  const navigate = useNavigate();
  const traceability = dpp?.traceability;
  const material = dpp?.transparency?.material;
  const carbon = dpp?.transparency?.environmental?.carbon_footprint;
  const technical = dpp?.transparency?.technical;
  const dimensions = technical?.dimensions;
  const disassembly = technical?.disassembly;
  const epd = dpp?.trust?.epd;
  const [activeTab, setActiveTab] = useState<TabValue>('traceability');
  const [pilots, setPilots] = useState<BimFileDto[]>([]);
  const [pilotsLoading, setPilotsLoading] = useState(true);
  const [pilotsError, setPilotsError] = useState<string | null>(null);
  // Fetched by id, not looked up in `pilots`: the link must resolve even if the
  // building is no longer a pilot or falls outside the list endpoint's limit.
  const [linked, setLinked] = useState<{
    id: string;
    building: BimFileDto | null;
  } | null>(null);
  const [picking, setPicking] = useState(false);
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);
  const [showBuildingDialog, setShowBuildingDialog] = useState(false);
  const [pilotQuery, setPilotQuery] = useState('');
  const [buildingSaving, setBuildingSaving] = useState(false);
  const [buildingError, setBuildingError] = useState<string | null>(null);
  const linkedId = component.bim_dataset_id;
  const linkedBuilding = linked?.id === linkedId ? linked.building : undefined;
  const visiblePilots = pilots.filter((bim) =>
    buildingName(bim.filename).toLowerCase().includes(pilotQuery.toLowerCase()),
  );

  useEffect(() => {
    let cancelled = false;
    listBimFiles()
      .then((rows) => {
        // Same rule as the Buildings & Pilots page: anything not an archetype is a pilot.
        if (!cancelled) setPilots(rows.filter((bim) => bim.category !== 'archetype'));
      })
      .catch(() => {
        if (!cancelled) setPilotsError('Buildings could not be loaded.');
      })
      .finally(() => {
        if (!cancelled) setPilotsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!linkedId) return;
    let cancelled = false;
    getBimFile(linkedId)
      .then((building) => {
        if (!cancelled) setLinked({ id: linkedId, building });
      })
      .catch(() => {
        if (!cancelled) setLinked({ id: linkedId, building: null });
      });
    return () => {
      cancelled = true;
    };
  }, [linkedId]);

  const saveBuilding = async (bimDatasetId: string | null) => {
    try {
      setBuildingSaving(true);
      setBuildingError(null);
      onUpdated(await updateComponentBuilding(component.id, bimDatasetId));
      setPicking(false);
      setConfirmingDisconnect(false);
      setPilotQuery('');
    } catch {
      setBuildingError('Building could not be updated.');
    } finally {
      setBuildingSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-[calc(100%-2rem)] max-w-5xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <div className="flex flex-col gap-3 pr-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-2">
              <DialogTitle className="text-lg">{component.name}</DialogTitle>
              <DialogDescription>DPP</DialogDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="shrink-0"
              disabled={!component.ifc_object_key}
              title={component.ifc_object_key ? undefined : 'No IFC file available'}
              onClick={() => navigate(`/components/${component.id}/view`)}
            >
              <Eye /> View Component
            </Button>
          </div>
        </DialogHeader>

        <div className="min-h-0 space-y-5 overflow-y-auto px-4 py-5 sm:px-6">
          <section className="grid gap-3 sm:grid-cols-[2fr_1fr]">
            <div className="overflow-hidden rounded-xl border bg-muted">
              {component.photo_object_key ? (
                <img
                  src={getComponentFileUrl(component.id, 'photo')}
                  alt={component.name}
                  className="h-full max-h-80 w-full object-contain"
                />
              ) : (
                <div className="flex h-full min-h-40 items-center justify-center text-sm text-muted-foreground">
                  No photo
                </div>
              )}
            </div>
            <div className="flex flex-col items-center justify-center gap-2 rounded-xl border bg-card p-4">
              {component.qr_object_key ? (
                <img
                  src={getComponentFileUrl(component.id, 'qr')}
                  alt={`QR code for ${component.name}`}
                  className="w-full max-w-48"
                />
              ) : (
                <span className="text-sm text-muted-foreground">No QR code</span>
              )}
              {dpp?.['@id'] && (
                <p className="break-all text-center text-xs text-muted-foreground">
                  {dpp['@id']}
                </p>
              )}
            </div>
          </section>

          <div role="tablist" aria-label="DPP section" className="flex gap-5 border-b">
            {tabs.map((tab, index) => (
              <button
                key={tab.value}
                id={`component-tab-${tab.value}`}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.value}
                aria-controls="component-tabpanel"
                tabIndex={activeTab === tab.value ? 0 : -1}
                onClick={() => setActiveTab(tab.value)}
                onKeyDown={(event) => {
                  const step =
                    event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
                  if (!step) return;
                  event.preventDefault();
                  const next = tabs[(index + step + tabs.length) % tabs.length];
                  setActiveTab(next.value);
                  document.getElementById(`component-tab-${next.value}`)?.focus();
                }}
                className={cn(
                  'relative whitespace-nowrap pb-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground',
                  activeTab === tab.value &&
                    'text-primary after:absolute after:inset-x-0 after:-bottom-px after:h-0.5 after:bg-primary',
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div
            id="component-tabpanel"
            role="tabpanel"
            aria-labelledby={`component-tab-${activeTab}`}
            className="space-y-5"
          >
            {activeTab === 'traceability' && (
              <Section>
                <Field
                  label="Serial number"
                  value={traceability?.product_id?.serial_number}
                />
                <Field
                  label="Production date"
                  value={traceability?.product_id?.production_date}
                />
                <Field
                  label="Manufacturer"
                  value={
                    traceability?.manufacturer?.name &&
                    [traceability.manufacturer.name, traceability.manufacturer.country]
                      .filter(Boolean)
                      .join(', ')
                  }
                />
                <Field
                  label="Lifecycle stage"
                  value={
                    traceability?.lifecycle_stage?.value && (
                      <span className="capitalize">
                        {traceability.lifecycle_stage.value}
                      </span>
                    )
                  }
                />
                <Field label="Reuse cycles" value={traceability?.reuse_cycles?.value} />
              </Section>
            )}

            {activeTab === 'transparency' && (
              <>
                <Card className="shadow-none">
                  <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 pb-4">
                    <CardTitle className="text-sm font-medium">Materials</CardTitle>
                    {material?.circularity_class && (
                      <Badge>{material.circularity_class}</Badge>
                    )}
                  </CardHeader>
                  <CardContent>
                    {material?.materials?.length ? (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Material</TableHead>
                            <TableHead className="text-right">Weight</TableHead>
                            <TableHead className="text-right">Recycled content</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {material.materials.map((item, index) => (
                            <TableRow key={`${item.name ?? 'material'}-${index}`}>
                              <TableCell>{item.name ?? '--'}</TableCell>
                              <TableCell className="text-right">
                                {withUnit(item.weight_kg, 'kg') ?? '--'}
                              </TableCell>
                              <TableCell className="text-right">
                                {withUnit(item.recycled_content_pct, '%') ?? '--'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No materials recorded.
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Section title="Environmental">
                  <Field
                    label="Carbon footprint"
                    value={withUnit(carbon?.total_kg_co2eq, 'kgCO₂e')}
                  />
                  <Field label="Performance class" value={carbon?.performance_class} />
                </Section>

                <Section title="Technical">
                  <Field
                    label="Dimensions (W × H × T)"
                    value={
                      dimensions &&
                      [dimensions.width_m, dimensions.height_m, dimensions.thickness_m]
                        .map((value) => (typeof value === 'number' ? value : '--'))
                        .join(' × ') + ' m'
                    }
                  />
                  <Field
                    label="Fire reaction class"
                    value={technical?.fire_reaction_class}
                  />
                  <Field
                    label="Expected lifetime"
                    value={withUnit(technical?.expected_lifetime_years, 'years')}
                  />
                  <Field
                    label="Disassembly"
                    value={
                      disassembly?.connection_type &&
                      `${disassembly.connection_type}${disassembly.reversible ? ' (reversible)' : ''}`
                    }
                  />
                  <Field
                    label="End of life"
                    value={
                      technical?.end_of_life_scenario && (
                        <span className="capitalize">
                          {technical.end_of_life_scenario}
                        </span>
                      )
                    }
                  />
                </Section>
              </>
            )}

            {activeTab === 'trust' && (
              <Section>
                <Field label="EPD" value={epd?.epd_id} />
                <Field label="EPD valid until" value={epd?.valid_until} />
              </Section>
            )}

            {activeTab === 'sensors' && <ComponentSensorsTab component={component} />}

            {activeTab === 'building' && (
              <Card className="shadow-none">
                <CardContent className="space-y-4 pt-6 text-sm">
                  {linkedId ? (
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <Field
                        label="Connected to"
                        value={
                          linkedBuilding === undefined ? (
                            <span className="text-muted-foreground">Loading…</span>
                          ) : linkedBuilding ? (
                            <Button
                              type="button"
                              variant="link"
                              title={linkedBuilding.filename}
                              onClick={() => setShowBuildingDialog(true)}
                              className="h-auto max-w-full justify-start truncate p-0"
                            >
                              {buildingName(linkedBuilding.filename)}
                            </Button>
                          ) : (
                            <span className="text-destructive">
                              Building could not be loaded.
                            </span>
                          )
                        }
                      />
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={buildingSaving}
                          onClick={() => setPicking(true)}
                        >
                          Change
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={buildingSaving}
                          onClick={() => setConfirmingDisconnect(true)}
                        >
                          Disconnect
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3 py-6 text-center">
                      <p className="text-muted-foreground">
                        This component is not connected to a building.
                      </p>
                      <Button type="button" size="sm" onClick={() => setPicking(true)}>
                        Connect to building
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </DialogContent>
      <Dialog
        open={picking}
        onOpenChange={(open) => {
          if (buildingSaving) return;
          setPicking(open);
          setPilotQuery('');
          setBuildingError(null);
        }}
      >
        <DialogContent className="flex max-h-[80vh] w-[calc(100%-2rem)] max-w-md flex-col gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b border-border px-6 py-4 text-left">
            <DialogTitle className="text-lg">Connect to building</DialogTitle>
            <DialogDescription>
              Select a pilot building for {component.name}.
            </DialogDescription>
          </DialogHeader>
          <div className="px-4 pt-4 sm:px-6">
            <SearchInput
              value={pilotQuery}
              onChange={setPilotQuery}
              placeholder="Search buildings…"
              className="sm:max-w-none"
            />
          </div>
          <div className="max-h-72 min-h-0 space-y-3 overflow-y-auto px-4 py-4 text-sm sm:px-6">
            {pilotsLoading ? (
              <p className="text-muted-foreground">Loading buildings…</p>
            ) : pilotsError ? (
              <p className="text-destructive">{pilotsError}</p>
            ) : visiblePilots.length ? (
              <ul className="divide-y rounded-lg border">
                {visiblePilots.map((bim) => (
                  <li key={bim.id}>
                    <button
                      type="button"
                      disabled={buildingSaving || bim.id === linkedId}
                      onClick={() => saveBuilding(bim.id)}
                      className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
                    >
                      <span className="truncate">{buildingName(bim.filename)}</span>
                      {bim.id === linkedId && (
                        <span className="text-xs text-muted-foreground">Current</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">
                {pilots.length
                  ? 'No buildings match the current search.'
                  : 'No pilot buildings available.'}
              </p>
            )}
            {buildingError && <p className="text-destructive">{buildingError}</p>}
          </div>
        </DialogContent>
      </Dialog>
      <Dialog
        open={confirmingDisconnect}
        onOpenChange={(open) => {
          if (buildingSaving) return;
          setConfirmingDisconnect(open);
          setBuildingError(null);
        }}
      >
        <DialogContent className="w-[calc(100%-2rem)] max-w-md">
          <DialogHeader className="text-left">
            <DialogTitle>Disconnect building?</DialogTitle>
            <DialogDescription>
              {component.name} will no longer be connected to{' '}
              {linkedBuilding ? buildingName(linkedBuilding.filename) : 'its building'}.
            </DialogDescription>
          </DialogHeader>
          {buildingError && <p className="text-sm text-destructive">{buildingError}</p>}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={buildingSaving}
              onClick={() => setConfirmingDisconnect(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={buildingSaving}
              onClick={() => saveBuilding(null)}
            >
              {buildingSaving ? 'Disconnecting…' : 'Disconnect'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {linkedBuilding && showBuildingDialog && (
        <BIMDetailsDialog
          file={linkedBuilding}
          onClose={() => setShowBuildingDialog(false)}
        />
      )}
    </Dialog>
  );
}
