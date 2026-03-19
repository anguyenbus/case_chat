import Icon from '@/components/ui/icon'
import MarkdownRenderer from '@/components/ui/typography/MarkdownRenderer'
import { useStore } from '@/store'
import type { ChatMessage, ReferenceData } from '@/types/os'
import Videos from './Multimedia/Videos'
import Images from './Multimedia/Images'
import Audios from './Multimedia/Audios'
import { memo, useState } from 'react'
import AgentThinkingLoader from './AgentThinkingLoader'
import CitationLink from '../CitationLink'
import CitationPanel from '../CitationPanel'

interface MessageProps {
  message: ChatMessage
}

const AgentMessage = ({ message }: MessageProps) => {
  const { streamingErrorMessage } = useStore()
  const [citationPanelOpen, setCitationPanelOpen] = useState(false)
  const [selectedReferences, setSelectedReferences] = useState<ReferenceData[]>(
    []
  )

  /**
   * Handles citation link click to show panel.
   */
  const handleCitationClick = (references: ReferenceData[]) => {
    setSelectedReferences(references)
    setCitationPanelOpen(true)
  }

  let messageContent
  if (message.streamingError) {
    messageContent = (
      <p className="text-destructive">
        Oops! Something went wrong while streaming.{' '}
        {streamingErrorMessage ? (
          <>{streamingErrorMessage}</>
        ) : (
          'Please try refreshing the page or try again later.'
        )}
      </p>
    )
  } else if (message.content) {
    messageContent = (
      <div className="flex w-full flex-col gap-4">
        <MarkdownRenderer>{message.content}</MarkdownRenderer>

        {/* Citation links */}
        {message.extra_data?.references &&
          message.extra_data.references.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {message.extra_data.references.map((refData, index) => (
                <CitationLink
                  key={index}
                  citationNumber={index + 1}
                  references={message.extra_data?.references || []}
                  onCitationClick={handleCitationClick}
                />
              ))}
            </div>
          )}

        {message.videos && message.videos.length > 0 && (
          <Videos videos={message.videos} />
        )}
        {message.images && message.images.length > 0 && (
          <Images images={message.images} />
        )}
        {message.audio && message.audio.length > 0 && (
          <Audios audio={message.audio} />
        )}

        {/* Citation panel */}
        <CitationPanel
          isOpen={citationPanelOpen}
          onClose={() => setCitationPanelOpen(false)}
          references={selectedReferences}
        />
      </div>
    )
  } else if (message.response_audio) {
    if (!message.response_audio.transcript) {
      messageContent = (
        <div className="mt-2 flex items-start">
          <AgentThinkingLoader />
        </div>
      )
    } else {
      messageContent = (
        <div className="flex w-full flex-col gap-4">
          <MarkdownRenderer>
            {message.response_audio.transcript}
          </MarkdownRenderer>

          {/* Citation links for audio responses */}
          {message.extra_data?.references &&
            message.extra_data.references.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {message.extra_data.references.map((refData, index) => (
                  <CitationLink
                    key={index}
                    citationNumber={index + 1}
                    references={message.extra_data?.references || []}
                    onCitationClick={handleCitationClick}
                  />
                ))}
              </div>
            )}

          {message.response_audio.content && message.response_audio && (
            <Audios audio={[message.response_audio]} />
          )}

          {/* Citation panel */}
          <CitationPanel
            isOpen={citationPanelOpen}
            onClose={() => setCitationPanelOpen(false)}
            references={selectedReferences}
          />
        </div>
      )
    }
  } else {
    messageContent = (
      <div className="mt-2">
        <AgentThinkingLoader />
      </div>
    )
  }

  return (
    <div className="flex flex-row items-start gap-4 font-geist">
      <div className="flex-shrink-0">
        <Icon type="agent" size="sm" />
      </div>
      {messageContent}
    </div>
  )
}

const UserMessage = memo(({ message }: MessageProps) => {
  return (
    <div className="flex items-start gap-4 pt-4 text-start max-md:break-words">
      <div className="flex-shrink-0">
        <Icon type="user" size="sm" />
      </div>
      <div className="text-md rounded-lg font-geist text-secondary">
        {message.content}
      </div>
    </div>
  )
})

AgentMessage.displayName = 'AgentMessage'
UserMessage.displayName = 'UserMessage'
export { AgentMessage, UserMessage }
