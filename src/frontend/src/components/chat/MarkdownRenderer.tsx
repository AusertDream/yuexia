import { memo, useCallback, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'

interface Props {
  content: string
}

function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {})
  }, [code])

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
    >
      {copied ? '已复制' : '复制'}
    </button>
  )
}

function MarkdownRenderer({ content }: Props) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const isBlock = match || (typeof children === 'string' && children.includes('\n'))

            if (isBlock) {
              const codeStr = String(children).replace(/\n$/, '')
              return (
                <div className="relative group my-3">
                  {match && (
                    <span className="absolute top-0 left-0 px-2 py-0.5 text-[10px] text-gray-400 bg-gray-800/80 rounded-br font-mono">
                      {match[1]}
                    </span>
                  )}
                  <CopyButton code={codeStr} />
                  <pre className="!bg-[#0d1117] !border !border-gray-700/50 !rounded-lg !p-4 !pt-7 overflow-x-auto custom-scrollbar">
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                </div>
              )
            }

            // 行内代码
            return (
              <code
                className="px-1.5 py-0.5 rounded text-[13px] bg-[var(--panel-bg-alt)] text-[var(--accent-blue)] border border-gray-700/40 font-mono"
                {...props}
              >
                {children}
              </code>
            )
          },
          a({ href, children, ...props }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent-blue)] hover:underline"
                {...props}
              >
                {children}
              </a>
            )
          },
          table({ children, ...props }) {
            return (
              <div className="overflow-x-auto my-3">
                <table className="min-w-full border-collapse border border-gray-700/50 text-sm" {...props}>
                  {children}
                </table>
              </div>
            )
          },
          th({ children, ...props }) {
            return (
              <th className="border border-gray-700/50 px-3 py-1.5 bg-[var(--panel-bg-alt)] text-left font-medium" {...props}>
                {children}
              </th>
            )
          },
          td({ children, ...props }) {
            return (
              <td className="border border-gray-700/50 px-3 py-1.5" {...props}>
                {children}
              </td>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default memo(MarkdownRenderer)
