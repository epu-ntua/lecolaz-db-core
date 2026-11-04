import { useEffect, useId, useRef, useState } from 'react';
import { Box, Building2, Check, ChevronDown, Link, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

export type AssignmentOption = {
  value: string;
  label: string;
  description?: string;
  kind: 'action' | 'building' | 'component';
};

const GROUPS = [
  { kind: 'action', label: 'Assignment' },
  { kind: 'building', label: 'Buildings' },
  { kind: 'component', label: 'Components' },
] as const;

export function SensorAssignmentPicker({
  options,
  value,
  onChange,
  disabled,
}: {
  options: AssignmentOption[];
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const selected = options.find((option) => option.value === value);
  const visible = options.filter((option) =>
    [option.label, option.description].some((text) =>
      text?.toLowerCase().includes(query.trim().toLowerCase()),
    ),
  );
  const Icon = open
    ? Search
    : selected?.kind === 'building'
      ? Building2
      : selected?.kind === 'component'
        ? Box
        : Link;
  const selectedLabel = selected
    ? `${selected.kind === 'building' ? 'Building · ' : selected.kind === 'component' ? 'Component · ' : ''}${selected.label}`
    : 'Choose a building or component';

  useEffect(() => {
    if (open) {
      list.current?.scrollIntoView({ block: 'nearest' });
      list.current
        ?.querySelectorAll('[role="option"]')
        [active]?.scrollIntoView({ block: 'nearest' });
    }
  }, [active, open, query]);

  const showOptions = () => {
    setQuery('');
    setActive(
      Math.max(
        0,
        options.findIndex((option) => option.value === value),
      ),
    );
    setOpen(true);
  };
  const choose = (option: AssignmentOption) => {
    if (disabled) return;
    onChange(option.value);
    setOpen(false);
  };

  return (
    <div
      className="grid gap-2 sm:col-span-2"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <label htmlFor={id} className="text-sm font-medium">
        Connect to
      </label>
      <div className="relative">
        <Icon
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground"
        />
        <input
          ref={input}
          id={id}
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-options`}
          aria-activedescendant={
            open && visible[active] ? `${id}-option-${active}` : undefined
          }
          autoComplete="off"
          disabled={disabled}
          className="field pl-9 pr-10"
          value={open ? query : selectedLabel}
          placeholder="Search buildings or components…"
          onClick={() => {
            if (!open) showOptions();
          }}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
            setOpen(true);
          }}
          onKeyDown={(event) => {
            if (
              !open &&
              event.key.length === 1 &&
              !event.ctrlKey &&
              !event.metaKey &&
              !event.altKey
            ) {
              event.preventDefault();
              setQuery(event.key);
              setActive(0);
              setOpen(true);
            } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
              event.preventDefault();
              if (!open) showOptions();
              else
                setActive((current) =>
                  Math.max(
                    0,
                    Math.min(
                      visible.length - 1,
                      current + (event.key === 'ArrowDown' ? 1 : -1),
                    ),
                  ),
                );
            } else if (event.key === 'Enter' && open) {
              event.preventDefault();
              if (visible[active]) choose(visible[active]);
            } else if (event.key === 'Escape' && open) {
              event.preventDefault();
              event.stopPropagation();
              setOpen(false);
            } else if (
              open &&
              (event.key === 'Home' || event.key === 'End') &&
              event.ctrlKey
            ) {
              event.preventDefault();
              setActive(event.key === 'Home' ? 0 : Math.max(0, visible.length - 1));
            }
          }}
          onFocus={(event) => event.target.select()}
        />
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          aria-label={open ? 'Close connections' : 'Show connections'}
          className="absolute right-2 top-2 rounded p-1 text-muted-foreground hover:text-foreground"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => {
            input.current?.focus();
            if (open) setOpen(false);
            else showOptions();
          }}
        >
          <ChevronDown className="h-4 w-4" />
        </button>
      </div>
      {open && (
        <div
          ref={list}
          id={`${id}-options`}
          role="listbox"
          aria-label="Sensor connection"
          className="max-h-60 overflow-y-auto rounded-lg border bg-card p-1"
        >
          {GROUPS.map((group) => {
            const entries = visible.filter((option) => option.kind === group.kind);
            if (!entries.length) return null;
            return (
              <div key={group.kind} role="group" aria-labelledby={`${id}-${group.kind}`}>
                <div
                  id={`${id}-${group.kind}`}
                  className="px-3 py-2 text-xs font-semibold text-muted-foreground"
                >
                  {group.label}
                </div>
                {entries.map((option) => {
                  const index = visible.indexOf(option);
                  const OptionIcon =
                    option.kind === 'building'
                      ? Building2
                      : option.kind === 'component'
                        ? Box
                        : Link;
                  return (
                    <div
                      key={option.value}
                      id={`${id}-option-${index}`}
                      role="option"
                      aria-selected={option.value === value}
                      className={cn(
                        'flex cursor-pointer items-start gap-3 rounded-md px-3 py-2 text-sm',
                        index === active && 'bg-accent text-accent-foreground',
                      )}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseMove={() => setActive(index)}
                      onClick={() => choose(option)}
                    >
                      <OptionIcon
                        aria-hidden="true"
                        className="mt-0.5 h-4 w-4 shrink-0"
                      />
                      <span className="min-w-0 flex-1 break-words">
                        <span className="block">{option.label}</span>
                        {option.description && (
                          <span className="block text-xs text-muted-foreground">
                            {option.description}
                          </span>
                        )}
                      </span>
                      {option.value === value && (
                        <Check aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
          {!visible.length && (
            <div className="p-3 text-sm text-muted-foreground" role="status">
              No connections match your search.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
