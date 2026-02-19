import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * A utility for cleanly merging Tailwind CSS classes.
 * * 1. Resolves Conflicts: Uses 'tailwind-merge' to ensure that if you pass
 * conflicting classes (e.g., 'px-2' and 'px-4'), the last one wins.
 * 2. Conditional Logic: Uses 'clsx' to allow toggling classes based on
 * boolean logic without template literal mess.
 * * @example
 * cn("base-style", isActive && "active-style", props.className)
 */

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
