'use client'

/**
 * CitationLink component.
 *
 * Clickable citation link in chat messages for opening
 * the citation panel.
 *
 * @module ChatArea/CitationLink
 */

import { type FC, useState } from 'react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'
import type { ReferenceData } from '@/types/os'

/**
 * Props for CitationLink component.
 */
export interface CitationLinkProps {
  /** Citation number to display */
  citationNumber: number
  /** Reference data for this citation */
  references: ReferenceData[]
  /** Callback when citation is clicked */
  onCitationClick: (references: ReferenceData[]) => void
  /** Whether this citation is selected */
  isSelected?: boolean
}

/**
 * Citation link component for chat messages.
 *
 * Features:
 * - Displays citation number in superscript brackets
 * - Clickable to open citation panel
 * - Tooltip showing document names on hover
 * - Highlighted when selected
 * - Styled as inline link
 * - Accessible with proper ARIA labels
 *
 * @example
 * ```tsx
 * <CitationLink
 *   citationNumber={1}
 *   references={references}
 *   onCitationClick={(refs) => setShowCitationPanel(true)}
 * />
 * ```
 */
const CitationLink: FC<CitationLinkProps> = ({
  citationNumber,
  references,
  onCitationClick,
  isSelected = false
}) => {
  const [isHovered, setIsHovered] = useState(false)

  /**
   * Formats tooltip content with document names.
   */
  const tooltipContent = references
    .map((ref) => ref.references.map((r) => r.name).join(', '))
    .join('; ')

  /**
   * Handles citation link click.
   */
  const handleClick = () => {
    onCitationClick(references)
  }

  return (
    <TooltipProvider>
      <Tooltip open={isHovered} onOpenChange={setIsHovered}>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={handleClick}
            className={cn(
              'ml-1 inline-flex h-5 items-center justify-center rounded px-1.5 text-xs font-medium transition-colors',
              'hover:bg-primary/20 hover:text-primary',
              'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
              isSelected
                ? 'text-primary-foreground bg-primary'
                : 'bg-primary/10 text-primary'
            )}
            aria-label={`View citation ${citationNumber}`}
          >
            [{citationNumber}]
          </button>
        </TooltipTrigger>
        <TooltipContent>
          <p className="max-w-xs truncate">{tooltipContent}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export default CitationLink
