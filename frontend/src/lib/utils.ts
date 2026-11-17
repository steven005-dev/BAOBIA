import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Fusionne des classes Tailwind (utilitaire attendu par shadcn/ui). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
