import type { ReactNode } from 'react';
import { Download } from 'lucide-react';
import { getComponentFileUrl } from '@/api/components';
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
import type { ModularComponentDto } from '@/types/api/components';

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="text-sm">
      <div className="text-muted-foreground">{label}</div>
      <div>{value ?? '--'}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="shadow-none">
      <CardHeader className="pb-4">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 break-words md:grid-cols-2">
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
}: {
  component: ModularComponentDto;
  onClose: () => void;
}) {
  const dpp = component.dpp;
  const traceability = dpp?.traceability;
  const material = dpp?.transparency?.material;
  const carbon = dpp?.transparency?.environmental?.carbon_footprint;
  const technical = dpp?.transparency?.technical;
  const dimensions = technical?.dimensions;
  const disassembly = technical?.disassembly;
  const epd = dpp?.trust?.epd;

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-[calc(100%-2rem)] max-w-5xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <div className="flex flex-col gap-3 pr-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-2">
              <DialogTitle className="text-lg">{component.name}</DialogTitle>
              <DialogDescription>DPP</DialogDescription>
            </div>
            {component.ifc_object_key && (
              <Button asChild variant="outline" size="sm" className="shrink-0">
                <a href={getComponentFileUrl(component.id, 'ifc')} download>
                  <Download />
                  Download IFC
                </a>
              </Button>
            )}
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

          <Section title="Traceability">
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
                  <span className="capitalize">{traceability.lifecycle_stage.value}</span>
                )
              }
            />
            <Field label="Reuse cycles" value={traceability?.reuse_cycles?.value} />
          </Section>

          <Card className="shadow-none">
            <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 pb-4">
              <CardTitle className="text-sm font-medium">Materials</CardTitle>
              {material?.circularity_class && <Badge>{material.circularity_class}</Badge>}
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
                <p className="text-sm text-muted-foreground">No materials recorded.</p>
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
            <Field label="Fire reaction class" value={technical?.fire_reaction_class} />
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
                  <span className="capitalize">{technical.end_of_life_scenario}</span>
                )
              }
            />
          </Section>

          <Section title="Trust">
            <Field label="EPD" value={epd?.epd_id} />
            <Field label="EPD valid until" value={epd?.valid_until} />
          </Section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
