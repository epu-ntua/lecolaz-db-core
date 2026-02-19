import { BIMFilesTable } from "@/pages/BIM/components/BIMFilesTable";

export default function BIMPage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-2xl font-bold tracking-tight">BIM files</h1>
        <p className="text-sm text-muted-foreground">
          BIM records linked to uploaded files.
        </p>
      </header>

      <section>
        <BIMFilesTable refreshKey={0} />
      </section>
    </div>
  );
}