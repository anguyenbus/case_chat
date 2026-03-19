'use client'

import { motion } from 'framer-motion'

const ChatBlankState = () => {
  return (
    <section
      className="flex flex-col items-center text-center font-geist"
      aria-label="Welcome message"
    >
      <div className="flex max-w-3xl flex-col gap-y-6">
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="text-3xl font-[600] tracking-tight"
        >
          <div className="flex items-center justify-center font-medium">
            <span>Hi, I am your case assistant.</span>
          </div>
          <p className="mt-4 text-xl font-normal text-neutral-400">
            Please feel free to upload your case document and we can discuss.
          </p>
        </motion.h1>
      </div>
    </section>
  )
}

export default ChatBlankState
