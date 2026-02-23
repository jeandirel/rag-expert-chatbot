import { useState, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
    timestamp: Date;
    isStreaming?: boolean;
}

export interface Source {
    document_id: string;
    filename: string;
    page_number?: number;
    score: number;
    excerpt: string;
    url?: string;
}

export interface UseChatOptions {
    conversationId?: string;
    onConversationCreated?: (id: string) => void;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useChat(options: UseChatOptions = {}) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string | undefined>(
          options.conversationId
        );
    const abortControllerRef = useRef<AbortController | null>(null);
    const queryClient = useQueryClient();

  // Genere un ID unique pour chaque message
  const generateId = () => Math.random().toString(36).substring(2, 9);

  // Envoyer un message avec streaming SSE
  const sendMessage = useCallback(
        async (content: string) => {
                if (!content.trim() || isLoading) return;

          // Annuler le stream precedent si actif
          if (abortControllerRef.current) {
                    abortControllerRef.current.abort();
          }

          const controller = new AbortController();
                abortControllerRef.current = controller;

          // Ajouter le message utilisateur
          const userMessage: Message = {
                    id: generateId(),
                    role: 'user',
                    content: content.trim(),
                    timestamp: new Date(),
          };

          setMessages((prev) => [...prev, userMessage]);
                setIsLoading(true);

          // Placeholder pour la reponse assistant
          const assistantId = generateId();
                const assistantMessage: Message = {
                          id: assistantId,
                          role: 'assistant',
                          content: '',
                          timestamp: new Date(),
                          isStreaming: true,
                };

          setMessages((prev) => [...prev, assistantMessage]);

          try {
                    const token = localStorage.getItem('access_token');
                    const headers: Record<string, string> = {
                                'Content-Type': 'application/json',
                                Accept: 'text/event-stream',
                    };
                    if (token) {
                                headers['Authorization'] = `Bearer ${token}`;
                    }

                  const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
                              method: 'POST',
                              headers,
                              body: JSON.stringify({
                                            message: content.trim(),
                                            conversation_id: conversationId,
                                            stream: true,
                              }),
                              signal: controller.signal,
                  });

                  if (!response.ok) {
                              throw new Error(`HTTP error! status: ${response.status}`);
                  }

                  const reader = response.body?.getReader();
                    if (!reader) throw new Error('No response body');

                  const decoder = new TextDecoder();
                    let fullContent = '';
                    let sources: Source[] = [];
                    let newConvId: string | undefined;

                  while (true) {
                              const { done, value } = await reader.read();
                              if (done) break;

                      const chunk = decoder.decode(value, { stream: true });
                              const lines = chunk.split('\n');

                      for (const line of lines) {
                                    if (line.startsWith('data: ')) {
                                                    const data = line.slice(6).trim();
                                                    if (data === '[DONE]') continue;

                                      try {
                                                        const parsed = JSON.parse(data);

                                                      if (parsed.type === 'token') {
                                                                          fullContent += parsed.content;
                                                                          setMessages((prev) =>
                                                                                                prev.map((m) =>
                                                                                                                        m.id === assistantId
                                                                                                                                 ? { ...m, content: fullContent }
                                                                                                                          : m
                                                                                                                             )
                                                                                                        );
                                                      } else if (parsed.type === 'sources') {
                                                                          sources = parsed.sources;
                                                      } else if (parsed.type === 'conversation_id') {
                                                                          newConvId = parsed.conversation_id;
                                                                          if (!conversationId) {
                                                                                                setConversationId(newConvId);
                                                                                                options.onConversationCreated?.(newConvId!);
                                                                          }
                                                      } else if (parsed.type === 'error') {
                                                                          throw new Error(parsed.message);
                                                      }
                                      } catch (e) {
                                                        // Ignorer les lignes non-JSON
                                      }
                                    }
                      }
                  }

                  // Finaliser le message avec les sources
                  setMessages((prev) =>
                              prev.map((m) =>
                                            m.id === assistantId
                                                     ? { ...m, content: fullContent, sources, isStreaming: false }
                                              : m
                                                 )
                                      );

                  // Invalider le cache des conversations
                  queryClient.invalidateQueries({ queryKey: ['conversations'] });
          } catch (error: unknown) {
                    if (error instanceof Error && error.name === 'AbortError') {
                                // Stream annule par l'utilisateur
                      setMessages((prev) =>
                                    prev.map((m) =>
                                                    m.id === assistantId ? { ...m, isStreaming: false } : m
                                                         )
                                            );
                                return;
                    }

                  console.error('Chat error:', error);
                    toast.error('Erreur lors de la communication avec le serveur');

                  setMessages((prev) =>
                              prev.map((m) =>
                                            m.id === assistantId
                                                     ? {
                                                                         ...m,
                                                                         content:
                                                                           "Desolee, une erreur s'est produite. Veuillez reessayer.",
                                                                         isStreaming: false,
                                                     }
                                              : m
                                                 )
                                      );
          } finally {
                    setIsLoading(false);
                    abortControllerRef.current = null;
          }
        },
        [isLoading, conversationId, options, queryClient]
      );

  // Arreter le streaming en cours
  const stopStreaming = useCallback(() => {
        if (abortControllerRef.current) {
                abortControllerRef.current.abort();
        }
  }, []);

  // Reinitialiser la conversation
  const resetChat = useCallback(() => {
        stopStreaming();
        setMessages([]);
        setConversationId(undefined);
  }, [stopStreaming]);

  // Regenerer la derniere reponse
  const regenerateLastResponse = useCallback(() => {
        const lastUserMessage = [...messages]
          .reverse()
          .find((m) => m.role === 'user');
        if (!lastUserMessage) return;

                                                 setMessages((prev) => {
                                                         const lastAssistantIdx = prev.map((m) => m.role).lastIndexOf('assistant');
                                                         if (lastAssistantIdx === -1) return prev;
                                                         return prev.slice(0, lastAssistantIdx);
                                                 });

                                                 sendMessage(lastUserMessage.content);
  }, [messages, sendMessage]);

  return {
        messages,
        isLoading,
        conversationId,
        sendMessage,
        stopStreaming,
        resetChat,
        regenerateLastResponse,
  };
}
