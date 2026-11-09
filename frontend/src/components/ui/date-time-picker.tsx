import { useRef, useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { Button } from '@/components/ui/button';

function displayDateTime(value: string) {
  if (!value) return '';
  const [date, time] = value.split('T');
  return `${date.split('-').reverse().join('-')} ${time.length === 5 ? `${time}:00` : time}`;
}

function parseDateTime(value: string) {
  const match = /^(\d{2})-(\d{2})-(\d{4}) (\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) return '';
  const [, day, month, year, hour, minute, second = '00'] = match;
  const iso = `${year}-${month}-${day}T${hour}:${minute}:${second}`;
  const date = new Date(`${iso}Z`);
  // Reject rolled-over dates such as 31 February, rather than querying another day.
  return Number(year) > 0 &&
    Number.isFinite(date.getTime()) &&
    date.toISOString().slice(0, 19) === iso
    ? iso
    : '';
}

/**
 * Native datetime-local fields use the browser's date format, which we cannot set.
 * A text field guarantees DD-MM-YYYY while retaining the native calendar picker
 * and ISO values for callers; both range fields share this conversion and validation.
 */
export function DateTimePicker({
  id,
  value,
  min,
  max,
  onChange,
}: {
  id: string;
  value: string;
  min?: string;
  max?: string;
  onChange?: (value: string) => void;
}) {
  const picker = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const invalid = !!draft && !parseDateTime(draft);
  return (
    <div className="relative flex gap-2">
      <input
        id={id}
        type="text"
        className="field min-w-0 flex-1"
        placeholder="DD-MM-YYYY HH:mm:ss"
        aria-invalid={invalid || undefined}
        title="DD-MM-YYYY HH:mm:ss (UTC)"
        value={draft ?? displayDateTime(value)}
        disabled={!onChange}
        onChange={(event) => {
          const next = event.target.value;
          setDraft(next);
          // Incomplete edits clear the query range and cancel any pending request.
          onChange?.(parseDateTime(next));
        }}
        onBlur={() => {
          if (draft !== null && (!draft || parseDateTime(draft))) setDraft(null);
        }}
      />
      <Button
        type="button"
        variant="outline"
        size="icon"
        aria-label="Open calendar"
        disabled={!onChange}
        onClick={() => picker.current?.showPicker()}
      >
        <CalendarDays />
      </Button>
      <input
        ref={picker}
        type="datetime-local"
        step="1"
        className="pointer-events-none absolute bottom-0 right-0 h-px w-px opacity-0"
        tabIndex={-1}
        aria-hidden="true"
        value={value}
        min={min}
        max={max}
        disabled={!onChange}
        onChange={(event) => {
          setDraft(null);
          onChange?.(event.target.value);
        }}
      />
    </div>
  );
}
