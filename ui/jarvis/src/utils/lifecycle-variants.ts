// ============================================================
//  Lifecycle Variants — Single Source of Truth
//  CVA-based variant system for all lifecycle-coloured elements.
//  Replaces the copy-pasted className maps scattered across
//  NexusNode, NodeEditor, ControlStrip, and WallView.
// ============================================================

import { cva, type VariantProps } from 'class-variance-authority';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Utility: merge Tailwind classes without specificity conflicts */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ─── Node Badge (inline state pill) ────────────────────────
export const lifecycleBadge = cva(
  'inline-flex items-center gap-1 px-2 py-0.5 rounded border font-bold uppercase tracking-widest',
  {
    variants: {
      lifecycle: {
        LOOSE:      'bg-cyan-950/40    border-cyan-500/40    text-cyan-400',
        FORMING:    'bg-amber-950/40   border-amber-500/40   text-amber-400',
        FROZEN:     'bg-emerald-950/40 border-emerald-500/40 text-emerald-400',
        SUPERSEDED: 'bg-indigo-950/40  border-indigo-500/40  text-indigo-400',
        KILLED:     'bg-red-950/40     border-red-900/40     text-red-400 opacity-70',
      },
      size: {
        xs:  'text-[8px]',
        sm:  'text-[10px]',
        md:  'text-xs',
        lg:  'text-sm',
      },
    },
    defaultVariants: {
      size: 'sm',
    },
  }
);

// ─── Node Card Container ────────────────────────────────────
export const lifecycleCard = cva(
  'rounded-lg border transition-all',
  {
    variants: {
      lifecycle: {
        LOOSE:      'border-cyan-500/20    bg-cyan-950/10    hover:border-cyan-500/40',
        FORMING:    'border-amber-500/20   bg-amber-950/10   hover:border-amber-500/40',
        FROZEN:     'border-emerald-500/30 bg-emerald-950/10 hover:border-emerald-500/50',
        SUPERSEDED: 'border-indigo-500/20  bg-indigo-950/10  opacity-60',
        KILLED:     'border-red-900/30     bg-red-950/10     opacity-40',
      },
      selected: {
        true:  'ring-1 ring-blue-500/60 shadow-[0_0_20px_rgba(59,130,246,0.15)]',
        false: '',
      },
    },
    defaultVariants: {
      selected: false,
    },
  }
);

// ─── Glow dot (status indicator) ───────────────────────────
export const lifecycleGlow = cva(
  'w-2 h-2 rounded-full',
  {
    variants: {
      lifecycle: {
        LOOSE:      'bg-cyan-400    shadow-[0_0_6px_rgba(34,211,238,0.8)]',
        FORMING:    'bg-amber-400   shadow-[0_0_6px_rgba(251,191,36,0.8)]  animate-pulse',
        FROZEN:     'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,1)]   animate-pulse',
        SUPERSEDED: 'bg-indigo-400  shadow-[0_0_6px_rgba(129,140,248,0.6)]',
        KILLED:     'bg-red-800',
      },
    },
  }
);

// ─── Action button base ─────────────────────────────────────
export const lifecycleButton = cva(
  'rounded uppercase tracking-widest text-xs font-bold py-3 px-4 border transition-all disabled:opacity-50',
  {
    variants: {
      intent: {
        promote:   'bg-emerald-600  hover:bg-emerald-500  border-transparent       text-white shadow-lg shadow-emerald-900/30',
        kill:      'bg-red-950/40   hover:bg-red-900/60   border-red-500/50        text-red-400',
        supersede: 'bg-blue-950/40  hover:bg-blue-800/60  border-blue-500/50       text-blue-400',
        neutral:   'bg-white/5      hover:bg-white/10     border-white/10          text-white/60',
      },
    },
  }
);

// ─── TypeScript helpers ─────────────────────────────────────
export type LifecycleVariant = NonNullable<VariantProps<typeof lifecycleBadge>['lifecycle']>;
export type BadgeSize = NonNullable<VariantProps<typeof lifecycleBadge>['size']>;

/** Lookup human-readable label for each lifecycle state */
export const LIFECYCLE_LABELS: Record<LifecycleVariant, string> = {
  LOOSE:      'Loose',
  FORMING:    'Forming',
  FROZEN:     'Frozen',
  SUPERSEDED: 'Superseded',
  KILLED:     'Killed',
};

/** Lookup short description for tooltip/context use */
export const LIFECYCLE_DESCRIPTIONS: Record<LifecycleVariant, string> = {
  LOOSE:      'Unvalidated — awaiting evidence',
  FORMING:    'Building confidence — multiple sources converging',
  FROZEN:     'Immutable — high confidence, locked for evolution',
  SUPERSEDED: 'Archived — replaced by a newer version',
  KILLED:     'Terminated — rejected as hallucination or duplicate',
};
