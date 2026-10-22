import { useId, useRef, useState } from 'react';
import { FileCheck2, UploadCloud, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export function FilePicker({
  file,
  onChange,
  accept,
  disabled = false,
  label = 'Choose a file',
}: {
  file: File | null;
  onChange: (file: File | null) => void;
  accept?: string;
  disabled?: boolean;
  label?: string;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const select = (next: File | null) => {
    if (
      next &&
      accept &&
      !accept
        .split(',')
        .some((extension) =>
          next.name.toLowerCase().endsWith(extension.trim().toLowerCase()),
        )
    ) {
      setError('Please choose a supported file: ' + accept);
      return;
    }
    setError('');
    onChange(next);
  };
  return (
    <div>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) select(event.dataTransfer.files[0] ?? null);
        }}
        className={cn(
          'relative rounded-xl border border-dashed bg-muted/40 transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-ring/20',
          dragging && 'border-primary bg-accent',
          disabled && 'pointer-events-none opacity-60',
        )}
      >
        <label
          htmlFor={id}
          className="flex cursor-pointer flex-col items-center gap-3 px-5 py-7 text-center"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl border bg-card text-primary">
            {file ? (
              <FileCheck2 className="h-5 w-5" />
            ) : (
              <UploadCloud className="h-5 w-5" />
            )}
          </span>
          <span className="max-w-full break-all text-sm font-medium">
            {file ? file.name : label}
          </span>
          <span className="text-xs text-muted-foreground">
            {file
              ? (file.size / 1024 / 1024).toFixed(2) + ' MB · Click to replace'
              : 'Click to browse or drag and drop'}
          </span>
          {accept && !file && (
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
              {accept.replaceAll('.', '').replaceAll(',', ' / ')}
            </span>
          )}
        </label>
        <input
          ref={input}
          id={id}
          type="file"
          accept={accept}
          disabled={disabled}
          className="sr-only"
          onChange={(event) => select(event.target.files?.[0] ?? null)}
        />
        {file && (
          <button
            type="button"
            aria-label="Remove selected file"
            disabled={disabled}
            className="absolute right-3 top-3 rounded p-1 text-muted-foreground hover:bg-muted"
            onClick={() => {
              select(null);
              if (input.current) input.current.value = '';
            }}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
