/**
 * Bouton BAOBIA : toujours une icône ET un mot (charte, principe 2).
 *
 * Variantes : primary (action principale, 60 px, une seule par écran),
 * secondary (52 px), danger (action destructive, couleur d'erreur, jamais le rouge
 * d'alerte), ghost (action discrète, 48 px).
 *
 * Exemple :
 *   <Button icon={CircleCheck} onClick={confirmer}>{mots.confirmer}</Button>
 *   <Button variant="secondary" icon={ArrowLeft} onClick={retour}>{mots.retour}</Button>
 *   <Button loading>{mots.envoyer}</Button>
 */

import { cva, type VariantProps } from 'class-variance-authority'
import { LoaderCircle, type LucideIcon } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 rounded-md px-5 text-button font-bold',
    'select-none transition-colors',
    'disabled:cursor-not-allowed disabled:border-border disabled:bg-muted disabled:text-muted-foreground',
  ],
  {
    variants: {
      variant: {
        primary:
          'h-touch-primary bg-primary text-primary-foreground hover:bg-primary-hover active:bg-primary-hover',
        secondary:
          'h-touch-secondary border-2 border-primary bg-surface text-primary hover:bg-accent active:bg-accent',
        danger:
          'h-touch-secondary bg-destructive text-destructive-foreground active:brightness-90',
        ghost: 'h-touch px-3 text-primary hover:bg-accent active:bg-accent',
      },
      fullWidth: { true: 'w-full', false: '' },
    },
    defaultVariants: { variant: 'primary', fullWidth: false },
  },
)

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'>,
    VariantProps<typeof buttonVariants> {
  /** Icône lucide-react affichée avant le mot (obligatoire, sauf cas très rare). */
  icon?: LucideIcon
  /** Le mot de l'action (vocabulaire officiel). */
  children: ReactNode
  /** Affiche un indicateur et bloque le bouton pendant l'envoi. */
  loading?: boolean
}

export function Button({
  icon: Icon,
  children,
  variant,
  fullWidth,
  loading = false,
  disabled,
  className,
  type = 'button',
  ...props
}: ButtonProps) {
  const ShownIcon = loading ? LoaderCircle : Icon
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, fullWidth }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {ShownIcon && (
        <ShownIcon aria-hidden className={cn('size-icon shrink-0', loading && 'animate-spin')} strokeWidth={2} />
      )}
      <span>{children}</span>
    </button>
  )
}

/** Alias de la charte (section 8). */
export const PrimaryButton = (props: Omit<ButtonProps, 'variant'>) => <Button {...props} variant="primary" />
export const SecondaryButton = (props: Omit<ButtonProps, 'variant'>) => <Button {...props} variant="secondary" />
export const DangerButton = (props: Omit<ButtonProps, 'variant'>) => <Button {...props} variant="danger" />
