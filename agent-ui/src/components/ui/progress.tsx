'use client'

/**
 * Progress component using Radix UI Progress primitive.
 *
 * Displays a progress bar for tracking document upload and processing status.
 * Fully accessible with ARIA attributes for screen readers.
 *
 * @module ui/progress
 */

import * as React from 'react'
import * as ProgressPrimitive from '@radix-ui/react-progress'

import { cn } from '@/lib/utils'

/**
 * Props for the Progress component.
 */
export interface ProgressProps
  extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  /**
   * Current progress value (0-100)
   */
  value?: number
}

/**
 * Progress component for displaying completion percentage.
 *
 * Uses Radix UI Progress primitive with full accessibility support.
 * Automatically clamps values between 0 and 100.
 *
 * @example
 * ```tsx
 * <Progress value={50} />
 * <Progress value={75} className="h-2" />
 * ```
 */
const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressProps
>(({ className, value = 0, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn(
      'relative h-2 w-full overflow-hidden rounded-full bg-primary/20',
      className
    )}
    {...props}
  >
    <ProgressPrimitive.Indicator
      className="h-full w-full flex-1 bg-primary transition-all duration-300 ease-in-out"
      style={{
        transform: `translateX(-${100 - Math.min(100, Math.max(0, value))}%)`
      }}
    />
  </ProgressPrimitive.Root>
))
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
