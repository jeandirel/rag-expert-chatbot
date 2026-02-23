import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
    Send,
    StopCircle,
    RefreshCw,
    Copy,
    Check,
    ChevronDown,
    FileText,
    Bot,
    User,
    Trash2,
    Plus,
} from 'lucide-react';
import clsx from 'clsx';
import { useChat, type Message, type Source } from '../../hooks/useChat';
import PDFViewer from './PDFViewer';

// Composant message individuel
function MessageBubble({ message, onCopy }: { message: Message; onCopy: (text: string) => void }) {
    const isUser = message.role === 'user';
    const [copied, setCopied] = useState(false);

  const handleCopy = () => {
        onCopy(message.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
  };

  return (
        <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={clsx('flex gap-3 group', isUser ? 'flex-row-reverse' : 'flex-row')}
              >
          {/* Avatar */}
              <div
                        className={clsx(
                                    'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1',
                                    isUser ? 'bg-blue-600' : 'bg-gray-700'
                                  )}
                      >
                {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
              </div>div>
        
          {/* Bulle */}
              <div className={clsx('max-w-[80%] flex flex-col gap-1', isUser ? 'items-end' : 'items-start')}>
                      <div
                                  className={clsx(
                                                'rounded-2xl px-4 py-3 text-sm',
                                                isUser
                                                  ? 'bg-blue-600 text-white rounded-tr-sm'
                                                  : 'bg-gray-800 text-gray-100 rounded-tl-sm'
                                              )}
                                >
                        {isUser ? (
                                              <p className="whitespace-pre-wrap">{message.content}</p>p>
                                            ) : (
                                              <div className="prose prose-invert prose-sm max-w-none">
                                                            <ReactMarkdown
                                                                              remarkPlugins={[remarkGfm]}
                                                                              components={{
                                                                                                  code({ node, className, children, ...props }: any) {
                                                                                                                        const match = /language-(\w+)/.exec(className || '');
                                                                                                                        const isInline = !match;
                                                                                                                        return isInline ? (
                                                                                                                                                <code className="bg-gray-700 rounded px-1 py-0.5 text-xs" {...props}>
                                                                                                                                                  {children}
                                                                                                                                                  </code>code>
                                                                                                                                              ) : (
                                                                                                                                                <SyntaxHighlighter
                                                                                                                                                                          style={oneDark as any}
                                                                                                                                                                          language={match[1]}
                                                                                                                                                                          PreTag="div"
                                                                                                                                                                          className="rounded-lg text-xs"
                                                                                                                                                                        >
                                                                                                                                                  {String(children).replace(/\n$/, '')}
                                                                                                                                                  </SyntaxHighlighter>SyntaxHighlighter>
                                                                                                                                              );
                                                                                                    },
                                                                              }}
                                                                            >
                                                              {message.content}
                                                            </ReactMarkdown>ReactMarkdown>
                                                {message.isStreaming && (
                                                                <span className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-1" />
                                                              )}
                                              </div>div>
                                )}
                      </div>div>
              
                {/* Sources */}
                {!isUser && message.sources && message.sources.length > 0 && (
                          <SourcesList sources={message.sources} />
                        )}
              
                {/* Actions */}
                {!isUser && !message.isStreaming && (
                          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                      <button
                                                      onClick={handleCopy}
                                                      className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
                                                      title="Copier"
                                                    >
                                        {copied ? <Check size={14} /> : <Copy size={14} />}
                                      </button>button>
                          </div>div>
                      )}
              
                      <span className="text-xs text-gray-500">
                        {new Date(message.timestamp).toLocaleTimeString('fr-FR', {
                            hour: '2-digit',
                            minute: '2-digit',
              })}
                      </span>span>
              </div>div>
        </motion.div>motion.div>
      );
}

// Liste des sources
function SourcesList({ sources }: { sources: Source[] }) {
    const [expanded, setExpanded] = useState(false);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  
    return (
          <div className="w-full mt-1">
                <button
                          onClick={() => setExpanded(!expanded)}
                          className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                        >
                        <FileText size={12} />
                        <span>{sources.length} source{sources.length > 1 ? 's' : ''}</span>span>
                        <ChevronDown
                                    size={12}
                                    className={clsx('transition-transform', expanded && 'rotate-180')}
                                  />
                </button>button>
          
                <AnimatePresence>
                  {expanded && (
                      <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                  >
                                  <div className="flex flex-col gap-2 mt-2">
                                    {sources.map((source, idx) => (
                                                    <div
                                                                        key={idx}
                                                                        className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs"
                                                                      >
                                                                      <div className="flex items-center justify-between mb-1">
                                                                                          <span className="font-medium text-gray-200 truncate">
                                                                                            {source.filename}
                                                                                            {source.page_number && (
                                                                                                <span className="text-gray-400 ml-1">p.{source.page_number}</span>span>
                                                                                                                )}
                                                                                            </span>span>
                                                                                          <div className="flex items-center gap-2 flex-shrink-0">
                                                                                                                <span className="text-green-400">
                                                                                                                  {Math.round(source.score * 100)}%
                                                                                                                  </span>span>
                                                                                            {source.filename.endsWith('.pdf') && (
                                                                                                <button
                                                                                                                            onClick={() => setPdfUrl(pdfUrl === source.url ? null : (source.url || null))}
                                                                                                                            className="text-blue-400 hover:text-blue-300 transition-colors"
                                                                                                                          >
                                                                                                                          <FileText size={12} />
                                                                                                  </button>button>
                                                                                                                )}
                                                                                            </div>div>
                                                                      </div>div>
                                                                      <p className="text-gray-400 line-clamp-3">{source.excerpt}</p>p>
                                                    </div>div>
                                                  ))}
                                  </div>div>
                      </motion.div>motion.div>
                    )}
                </AnimatePresence>AnimatePresence>
          
            {/* Visionneuse PDF */}
                <AnimatePresence>
                  {pdfUrl && (
                      <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    className="fixed inset-4 z-50 bg-gray-900 rounded-xl shadow-2xl border border-gray-700 overflow-hidden"
                                  >
                                  <PDFViewer url={pdfUrl} onClose={() => setPdfUrl(null)} />
                      </motion.div>motion.div>
                    )}
                </AnimatePresence>AnimatePresence>
          </div>div>
        );
}

// Zone de saisie
function ChatInput({
    onSend,
    onStop,
    isLoading,
}: {
    onSend: (msg: string) => void;
    onStop: () => void;
    isLoading: boolean;
}) {
    const [input, setInput] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);
  
    const handleSend = () => {
          if (!input.trim() || isLoading) return;
          onSend(input);
          setInput('');
          if (textareaRef.current) textareaRef.current.style.height = 'auto';
    };
  
    const handleKeyDown = (e: React.KeyboardEvent) => {
          if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
          }
    };
  
    const handleInput = () => {
          const ta = textareaRef.current;
          if (ta) {
                  ta.style.height = 'auto';
                  ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
          }
    };
  
    return (
          <div className="border-t border-gray-700 p-4 bg-gray-900">
                <div className="flex items-end gap-2 bg-gray-800 rounded-2xl border border-gray-700 px-4 py-3">
                        <textarea
                                    ref={textareaRef}
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    onInput={handleInput}
                                    placeholder="Posez votre question sur la documentation..."
                                    className="flex-1 bg-transparent text-gray-100 placeholder-gray-500 resize-none outline-none text-sm min-h-[24px] max-h-[200px]"
                                    rows={1}
                                    disabled={isLoading}
                                  />
                        <div className="flex gap-2 flex-shrink-0">
                          {isLoading ? (
                        <button
                                        onClick={onStop}
                                        className="p-2 rounded-xl bg-red-600 hover:bg-red-500 text-white transition-colors"
                                        title="Arreter"
                                      >
                                      <StopCircle size={18} />
                        </button>button>
                      ) : (
                        <button
                                        onClick={handleSend}
                                        disabled={!input.trim()}
                                        className="p-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white transition-colors"
                                        title="Envoyer (Enter)"
                                      >
                                      <Send size={18} />
                        </button>button>
                                  )}
                        </div>div>
                </div>div>
                <p className="text-xs text-gray-600 mt-2 text-center">
                        Shift+Entree pour sauter une ligne
                </p>p>
          </div>div>
        );
}

// Composant principal ChatWindow
export default function ChatWindow() {
    const [currentConvId, setCurrentConvId] = useState<string | undefined>();
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const { messages, isLoading, sendMessage, stopStreaming, resetChat, regenerateLastResponse } =
          useChat({
                  conversationId: currentConvId,
                  onConversationCreated: setCurrentConvId,
          });
  
    // Auto-scroll vers le bas
    useEffect(() => {
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);
  
    const handleCopy = (text: string) => {
          navigator.clipboard.writeText(text).catch(() => {});
    };
  
    return (
          <div className="flex flex-col h-full bg-gray-900">
            {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900">
                        <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                                              <Bot size={18} className="text-white" />
                                  </div>div>
                                  <div>
                                              <h1 className="text-white font-semibold text-sm">Assistant RAG Expert</h1>h1>
                                              <p className="text-gray-400 text-xs">
                                                {isLoading ? (
                            <span className="flex items-center gap-1">
                                              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                                              En train de repondre...
                            </span>span>
                          ) : (
                            'Pret a repondre'
                          )}
                                              </p>p>
                                  </div>div>
                        </div>div>
                        <div className="flex items-center gap-2">
                                  <button
                                                onClick={regenerateLastResponse}
                                                disabled={messages.length === 0 || isLoading}
                                                className="p-2 rounded-lg hover:bg-gray-800 disabled:opacity-30 text-gray-400 hover:text-white transition-colors"
                                                title="Regenerer la derniere reponse"
                                              >
                                              <RefreshCw size={16} />
                                  </button>button>
                                  <button
                                                onClick={resetChat}
                                                disabled={isLoading}
                                                className="p-2 rounded-lg hover:bg-gray-800 disabled:opacity-30 text-gray-400 hover:text-white transition-colors"
                                                title="Nouvelle conversation"
                                              >
                                              <Plus size={16} />
                                  </button>button>
                          {messages.length > 0 && (
                        <button
                                        onClick={resetChat}
                                        disabled={isLoading}
                                        className="p-2 rounded-lg hover:bg-gray-800 disabled:opacity-30 text-gray-400 hover:text-red-400 transition-colors"
                                        title="Effacer la conversation"
                                      >
                                      <Trash2 size={16} />
                        </button>button>
                                  )}
                        </div>div>
                </div>div>
          
            {/* Zone messages */}
                <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
                  {messages.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-center gap-4">
                                  <div className="w-16 h-16 rounded-full bg-blue-600/20 flex items-center justify-center">
                                                <Bot size={32} className="text-blue-400" />
                                  </div>div>
                                  <div>
                                                <h2 className="text-white font-semibold text-lg mb-2">
                                                                Comment puis-je vous aider ?
                                                </h2>h2>
                                                <p className="text-gray-400 text-sm max-w-md">
                                                                Posez vos questions sur la documentation. Je peux rechercher dans
                                                                tous vos documents SharePoint et PDF.
                                                </p>p>
                                  </div>div>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg mt-4">
                                    {[
                                        'Quelle est la procedure pour ...',
                                        'Resume le document sur ...',
                                        'Quelles sont les normes de ...',
                                        'Comment configurer ...',
                                      ].map((suggestion) => (
                                                        <button
                                                                            key={suggestion}
                                                                            onClick={() => sendMessage(suggestion)}
                                                                            className="text-left p-3 rounded-xl border border-gray-700 hover:border-blue-500 hover:bg-gray-800 text-gray-400 hover:text-white text-xs transition-all"
                                                                          >
                                                          {suggestion}
                                                        </button>button>
                                                      ))}
                                  </div>div>
                      </div>div>
                    ) : (
                      <>
                                  <AnimatePresence initial={false}>
                                    {messages.map((message) => (
                                        <MessageBubble
                                                            key={message.id}
                                                            message={message}
                                                            onCopy={handleCopy}
                                                          />
                                      ))}
                                  </AnimatePresence>AnimatePresence>
                                  <div ref={messagesEndRef} />
                      </>>
                    )}
                </div>div>
          
            {/* Zone saisie */}
                <ChatInput onSend={sendMessage} onStop={stopStreaming} isLoading={isLoading} />
          </div>div>
        );
}</></motion.div>
