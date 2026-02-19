export default function TopBar() {
  return (
    <header className="h-14 border-b border-border bg-background px-6 flex items-center justify-between">
      
      {/* Left side */}
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-medium tracking-tight">
          LeColaz Platform
        </h1>
      </div>

      {/* Right side (placeholder for future actions) */}
      <div className="flex items-center gap-4">
        <span className="text-xs text-muted-foreground">
          v0.1
        </span>
      </div>

    </header>
  );
}
