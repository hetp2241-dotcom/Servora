import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArrowDown,
  Download,
  FileText,
  Paperclip,
  Pin,
  PinOff,
  Search,
  Send,
  Smile,
  X,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api, ensureCsrf, websocketUrl } from "@/lib/api";
import { shortDate } from "@/lib/utils";
import type { ChatMessage, User } from "@/types/api";
import { useAuth } from "@/hooks/use-auth";
import { Empty, Loading, PageIntro } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ConversationPartner = User & {
  service_names: string[];
  last_message: string;
  unread_count: number;
  is_pinned: boolean;
  is_online: boolean;
  last_seen: string | null;
};

type FilterValue = "all" | "unread" | "providers" | "customers";

function humanizeLastSeen(value: string | null) {
  if (!value) return "Offline";
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.floor(diff / 60000));
  if (minutes < 2) return "Active now";
  if (minutes < 60) return `Last seen ${minutes}m ago`;
  const hours = Math.max(1, Math.floor(minutes / 60));
  if (hours < 24) return `Last seen ${hours}h ago`;
  const days = Math.max(1, Math.floor(hours / 24));
  return `Last seen ${days}d ago`;
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB"];
  let size = bytes / 1024;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

function ConversationListSkeleton() {
  return (
    <div className="space-y-2 p-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="flex animate-pulse items-center gap-3 rounded-2xl border p-3">
          <div className="size-10 rounded-full bg-secondary" />
          <div className="min-w-0 flex-1">
            <div className="h-4 w-24 rounded bg-secondary" />
            <div className="mt-2 h-3 w-32 rounded bg-secondary/70" />
          </div>
        </div>
      ))}
    </div>
  );
}

function MessageListSkeleton() {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className={`flex ${index % 2 === 0 ? "justify-start" : "justify-end"}`}>
          <div className="h-16 w-2/3 animate-pulse rounded-2xl bg-secondary" />
        </div>
      ))}
    </div>
  );
}

export default function MessagesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const partnerId = Number(params.get("partner")) || null;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterValue>("all");
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [attachmentPreview, setAttachmentPreview] = useState<string | null>(null);
  const [attachmentError, setAttachmentError] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showNewMessages, setShowNewMessages] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [partnerPresence, setPartnerPresence] = useState({ online: false, last_seen: null as string | null });
  const socket = useRef<WebSocket | null>(null);
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const typingTimer = useRef<number | null>(null);

  const partners = useQuery({
    queryKey: ["message-partners"],
    queryFn: async () => (await api.get<{ results: ConversationPartner[] }>("/messages/")).data.results,
    staleTime: 10_000,
  });

  const conversation = useQuery({
    queryKey: ["conversation", partnerId],
    enabled: !!partnerId,
    queryFn: async () =>
      (
        await api.get<{
          partner: User & { is_online: boolean; last_seen: string | null };
          messages: ChatMessage[];
          has_more: boolean;
        }>(`/messages/${partnerId}/?limit=25`)
      ).data,
  });

  const partner = useMemo(
    () => partners.data?.find((item) => item.id === partnerId) || conversation.data?.partner,
    [partners.data, partnerId, conversation.data],
  );

  const isPinned = partners.data?.find((item) => item.id === partnerId)?.is_pinned ?? false;

  useEffect(() => {
    if (!conversation.data) {
      setMessages([]);
      setHasMore(false);
      return;
    }

    setMessages(conversation.data.messages || []);
    setHasMore(Boolean(conversation.data.has_more));
    setPartnerPresence({ online: conversation.data.partner.is_online, last_seen: conversation.data.partner.last_seen });
  }, [conversation.data]);

  useEffect(() => {
    if (!partnerId) return;

    const ws = new WebSocket(websocketUrl(`/ws/chat/${partnerId}/`));
    socket.current = ws;

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data) as {
        type: string;
        message?: ChatMessage;
        message_ids?: number[];
        status?: string;
        timestamp?: string;
        user_id?: number;
        online?: boolean;
        last_seen?: string | null;
        is_typing?: boolean;
      };

      if (payload.type === "chat.message" && payload.message) {
        const incoming = payload.message;
        setMessages((old) => (old.some((item) => item.id === incoming.id) ? old : [...old, incoming]));
        if (incoming.sender_id !== user?.id && document.visibilityState === "hidden") {
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification(`New message from ${partner?.full_name ?? "Someone"}`, {
              body: incoming.message || incoming.attachment_name || "Sent an attachment",
              tag: `chat-${incoming.sender_id}`,
            }).onclick = () => {
              window.focus();
              setParams({ partner: String(incoming.sender_id) });
            };
          }
        }
      }

      if (payload.type === "chat.receipt") {
        setMessages((old) =>
          old.map((item) =>
            payload.message_ids?.includes(item.id)
              ? {
                  ...item,
                  delivered_at: payload.status === "seen" ? payload.timestamp ?? item.delivered_at : item.delivered_at,
                  seen_at: payload.status === "seen" ? payload.timestamp ?? item.seen_at : item.seen_at,
                }
              : item,
          ),
        );
      }

      if (payload.type === "chat.presence") {
        if (payload.user_id === partnerId) {
          setPartnerPresence({ online: Boolean(payload.online), last_seen: payload.last_seen ?? null });
        }
      }

      if (payload.type === "chat.typing") {
        if (payload.user_id === partnerId) {
          setIsTyping(Boolean(payload.is_typing));
        }
      }

      if (payload.type === "chat.event") {
        void queryClient.invalidateQueries({ queryKey: ["message-partners"] });
      }
    };

    return () => {
      ws.close();
      socket.current = null;
    };
  }, [partnerId, partner?.full_name, queryClient, setParams, user?.id]);

  useEffect(() => {
    if (!partnerId) return;
    void api.post(`/messages/${partnerId}/seen/`);
    void queryClient.invalidateQueries({ queryKey: ["message-partners"] });
  }, [partnerId, queryClient]);

  useEffect(() => {
    if (!partnerId) return;
    setShowNewMessages(false);
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [partnerId]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (Notification.permission === "default") {
      void Notification.requestPermission();
    }
  }, []);

  const filteredPartners = useMemo(() => {
    const searchQuery = search.trim().toLowerCase();
    return (partners.data || []).filter((item) => {
      const matchesQuery =
        !searchQuery ||
        [item.full_name, item.role, item.service_names.join(" "), item.last_message]
          .join(" ")
          .toLowerCase()
          .includes(searchQuery);
      const matchesFilter =
        filter === "all"
          ? true
          : filter === "unread"
            ? item.unread_count > 0
            : filter === "providers"
              ? item.role === "PROVIDER"
              : item.role === "CUSTOMER";
      return matchesQuery && matchesFilter;
    });
  }, [filter, partners.data, search]);

  const emitTyping = useCallback((typing: boolean) => {
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ action: "typing", is_typing: typing }));
    }
  }, []);

  useEffect(() => {
    if (!partnerId) return;
    if (text.trim()) {
      emitTyping(true);
      if (typingTimer.current) {
        window.clearTimeout(typingTimer.current);
      }
      typingTimer.current = window.setTimeout(() => emitTyping(false), 1500);
    } else {
      emitTyping(false);
    }
    return () => {
      if (typingTimer.current) {
        window.clearTimeout(typingTimer.current);
      }
      emitTyping(false);
    };
  }, [emitTyping, partnerId, text]);

  const scrollToBottom = useCallback(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTo({ top: messageListRef.current.scrollHeight, behavior: "smooth" });
      setShowNewMessages(false);
    }
  }, []);

  useEffect(() => {
    if (!messageListRef.current) return;
    const container = messageListRef.current;
    const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 80;
    if (nearBottom) {
      container.scrollTop = container.scrollHeight;
      setShowNewMessages(false);
    } else {
      setShowNewMessages(true);
    }
  }, [messages]);

  const handleAttachmentChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const allowedTypes = new Set([
      "image/jpeg",
      "image/png",
      "image/gif",
      "image/webp",
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/zip",
      "application/x-zip-compressed",
    ]);
    const extension = file.name.toLowerCase();
    const isAllowedExtension = [".pdf", ".docx", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".webp"].some((ext) => extension.endsWith(ext));

    if (!allowedTypes.has(file.type) && !isAllowedExtension) {
      setAttachmentError("Supported files: images, PDF, DOCX, and ZIP.");
      setAttachmentFile(null);
      setAttachmentPreview(null);
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setAttachmentError("Attachments must be 10 MB or smaller.");
      setAttachmentFile(null);
      setAttachmentPreview(null);
      return;
    }

    setAttachmentError("");
    setAttachmentFile(file);
    if (file.type.startsWith("image/")) {
      setAttachmentPreview(URL.createObjectURL(file));
    } else {
      setAttachmentPreview(null);
    }
  };

  useEffect(() => {
    return () => {
      if (attachmentPreview) {
        URL.revokeObjectURL(attachmentPreview);
      }
    };
  }, [attachmentPreview]);

  const sendMessage = useCallback(async () => {
    const value = text.trim();
    if (!partnerId) return;
    if (!value && !attachmentFile) return;

    setIsSending(true);
    try {
      await ensureCsrf();
      if (attachmentFile) {
        const data = new FormData();
        data.append("attachment", attachmentFile);
        if (value) data.append("message", value);
        await api.post(`/messages/${partnerId}/attachments/`, data);
        setAttachmentFile(null);
        setAttachmentPreview(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      } else if (socket.current?.readyState === WebSocket.OPEN) {
        socket.current.send(JSON.stringify({ message: value }));
      }
      setText("");
      await queryClient.invalidateQueries({ queryKey: ["message-partners"] });
      setTimeout(() => scrollToBottom(), 120);
    } finally {
      setIsSending(false);
      emitTyping(false);
    }
  }, [attachmentFile, emitTyping, partnerId, queryClient, scrollToBottom, text]);

  const loadOlderMessages = useCallback(async () => {
    if (!partnerId || !messages.length || !hasMore) return;
    const oldestMessage = messages[0];
    setLoadingOlder(true);
    try {
      const response = await api.get<{ messages: ChatMessage[]; has_more: boolean }>(`/messages/${partnerId}/?before=${oldestMessage.id}&limit=25`);
      setMessages((old) => [...response.data.messages, ...old]);
      setHasMore(Boolean(response.data.has_more));
    } finally {
      setLoadingOlder(false);
    }
  }, [hasMore, messages, partnerId]);

  const togglePin = useCallback(async () => {
    if (!partnerId) return;
    await ensureCsrf();
    await api.post(`/messages/${partnerId}/pin/`);
    await queryClient.invalidateQueries({ queryKey: ["message-partners"] });
  }, [partnerId, queryClient]);

  const displayPartner = partner ?? conversation.data?.partner;

  return (
    <>
      <PageIntro
        eyebrow="Real-time"
        title="Messages"
        description="Chat with your connected providers or customers using the existing Channels WebSocket and message history APIs."
      />
      <div className="grid min-h-[620px] overflow-hidden rounded-2xl border bg-background shadow-card md:grid-cols-[320px_1fr]">
        <aside className="flex min-h-[280px] flex-col border-b md:min-h-0 md:border-b-0 md:border-r">
          <div className="border-b p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-bold">Conversations</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {(["all", "unread", "providers", "customers"] as FilterValue[]).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setFilter(item)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${filter === item ? "bg-primary text-white" : "bg-secondary text-muted-foreground"}`}
                >
                  {item === "all" ? "All" : item === "unread" ? "Unread" : item === "providers" ? "Providers" : "Customers"}
                </button>
              ))}
            </div>
            <div className="relative mt-3">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search conversations"
                aria-label="Search conversations"
                className="h-10 pl-9 pr-9"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  aria-label="Clear conversation search"
                  className="absolute right-2 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <X className="size-4" />
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-auto">
            {partners.isLoading ? (
              <ConversationListSkeleton />
            ) : filteredPartners.length ? (
              filteredPartners.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setParams({ partner: String(item.id) })}
                  className={`flex w-full items-start gap-3 border-b p-4 text-left transition-colors hover:bg-secondary ${partnerId === item.id ? "bg-primary-soft" : ""}`}
                >
                  <div className="relative shrink-0">
                    <span className="grid size-10 place-items-center rounded-full bg-gradient-brand font-bold text-white">
                      {item.full_name.charAt(0)}
                    </span>
                    {item.is_online && <span className="absolute bottom-0 right-0 size-3 rounded-full border-2 border-background bg-success" />}
                  </div>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-bold">{item.full_name}</span>
                      {item.unread_count > 0 && <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white">{item.unread_count}</span>}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {item.service_names.length ? item.service_names.join(", ") : item.role === "PROVIDER" ? "Service provider" : "Customer"}
                    </span>
                    {item.last_message && <span className="mt-0.5 block truncate text-xs text-muted-foreground/80">{item.last_message}</span>}
                  </span>
                </button>
              ))
            ) : search.trim() || filter !== "all" ? (
              <p className="p-5 text-center text-sm text-muted-foreground">No conversations found</p>
            ) : (
              <div className="flex h-full min-h-60 flex-col items-center justify-center px-6 text-center">
                <div className="rounded-3xl border bg-secondary/20 p-8">
                  <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-primary-soft text-primary">
                    <Search className="size-8" />
                  </div>
                  <h3 className="mt-4 font-bold">No conversations yet.</h3>
                  <p className="mt-2 text-sm text-muted-foreground">Book a service to start your first conversation.</p>
                </div>
              </div>
            )}
          </div>
        </aside>

        {displayPartner ? (
          <section className="flex min-h-[420px] flex-col md:min-h-0">
            <header className="flex items-center justify-between gap-3 border-b p-3 sm:p-4">
              <div className="flex min-w-0 items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-full bg-gradient-brand font-bold text-white">
                  {displayPartner.full_name.charAt(0)}
                </span>
                <div className="min-w-0">
                  <p className="truncate font-bold">{displayPartner.full_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {partnerPresence.online ? "Online" : humanizeLastSeen(partnerPresence.last_seen)}
                  </p>
                </div>
              </div>
              <button type="button" aria-label={isPinned ? "Unpin conversation" : "Pin conversation"} onClick={togglePin} className="rounded-full p-2 hover:bg-secondary">
                {isPinned ? <PinOff className="size-4" /> : <Pin className="size-4" />}
              </button>
            </header>

            <div ref={messageListRef} className="flex-1 space-y-3 overflow-auto bg-secondary/30 p-3 sm:p-6">
              {conversation.isLoading ? (
                <MessageListSkeleton />
              ) : (
                <>
                  {hasMore && (
                    <div className="flex justify-center">
                      <Button variant="outline" size="sm" onClick={loadOlderMessages} disabled={loadingOlder}>
                        {loadingOlder ? "Loading..." : "Load older messages"}
                      </Button>
                    </div>
                  )}
                  {messages.map((item) => {
                    const mine = item.sender_id === user?.id;
                    return (
                      <div key={item.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${mine ? "rounded-br-sm bg-primary text-white" : "rounded-bl-sm border bg-background"}`}>
                          {item.attachment_url ? (
                            <div className="space-y-2">
                              {item.attachment_type.startsWith("image/") ? (
                                <img src={item.attachment_url} alt={item.attachment_name || "Attachment"} className="max-h-64 rounded-xl object-cover" />
                              ) : (
                                <div className="flex items-center gap-3 rounded-xl border border-dashed px-3 py-2">
                                  <div className="grid size-10 place-items-center rounded-xl bg-secondary/50">
                                    {item.attachment_type.includes("pdf") ? <FileText className="size-5" /> : item.attachment_type.includes("zip") ? <Archive className="size-5" /> : <Paperclip className="size-5" />}
                                  </div>
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate font-medium">{item.attachment_name || "Attachment"}</p>
                                    <p className="text-[10px] opacity-70">{formatFileSize(item.attachment_size || 0)}</p>
                                  </div>
                                  <a href={item.attachment_url} download target="_blank" rel="noreferrer" className="rounded-lg p-2 hover:bg-secondary/70">
                                    <Download className="size-4" />
                                  </a>
                                </div>
                              )}
                              {item.message ? <p className="whitespace-pre-wrap">{item.message}</p> : null}
                            </div>
                          ) : (
                            <p className="whitespace-pre-wrap">{item.message}</p>
                          )}
                          <div className={`mt-1 flex items-center justify-end gap-1 text-[10px] ${mine ? "text-white/60" : "text-muted-foreground"}`}>
                            <span>{shortDate(item.timestamp)}</span>
                            {mine && <span>{item.seen_at ? "✓✓" : item.delivered_at ? "✓" : ""}</span>}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </>
              )}
            </div>

            {showNewMessages && (
              <div className="sticky bottom-3 z-10 mx-auto mb-2 w-fit">
                <Button variant="outline" size="sm" onClick={scrollToBottom} className="gap-2 shadow-lg">
                  <ArrowDown className="size-3" /> New messages
                </Button>
              </div>
            )}

            <div className="border-t bg-background p-3 sm:p-4">
              {attachmentFile && (
                <div className="mb-3 flex items-center gap-3 rounded-2xl border bg-secondary/20 px-3 py-2">
                  {attachmentPreview ? (
                    <img src={attachmentPreview} alt="Selected attachment preview" className="size-16 rounded-xl object-cover" />
                  ) : (
                    <div className="grid size-16 place-items-center rounded-xl bg-secondary">
                      {attachmentFile.name.toLowerCase().endsWith(".pdf") ? <FileText className="size-6" /> : attachmentFile.name.toLowerCase().endsWith(".zip") ? <Archive className="size-6" /> : <Paperclip className="size-6" />}
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{attachmentFile.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(attachmentFile.size)}</p>
                  </div>
                  <button type="button" onClick={() => { setAttachmentFile(null); setAttachmentPreview(null); setAttachmentError(""); if (fileInputRef.current) fileInputRef.current.value = ""; }} className="rounded-full p-2 hover:bg-secondary">
                    <X className="size-4" />
                  </button>
                </div>
              )}
              {attachmentError && <p className="mb-2 text-xs text-destructive">{attachmentError}</p>}
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <div className="relative">
                    <textarea
                      ref={composerRef}
                      value={text}
                      onChange={(event) => setText(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                          event.preventDefault();
                          void sendMessage();
                        }
                      }}
                      placeholder="Write a message"
                      rows={1}
                      className="min-h-[52px] w-full resize-none rounded-2xl border bg-background px-4 py-3 pr-12 text-sm outline-none focus:ring-2 focus:ring-primary"
                    />
                    <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
                      <button
                        type="button"
                        className="rounded-full p-1.5 hover:bg-secondary"
                        aria-label="Add emoji"
                        onClick={() => {
                          const emojiList = ["😊", "😂", "❤️", "👍", "🎉", "🔥", "💬", "✨", "🤝", "😄"];
                          const emoji = emojiList[Math.floor(Math.random() * emojiList.length)];
                          const start = composerRef.current?.selectionStart ?? text.length;
                          const end = composerRef.current?.selectionEnd ?? text.length;
                          const next = `${text.slice(0, start)}${emoji}${text.slice(end)}`;
                          setText(next);
                          requestAnimationFrame(() => {
                            composerRef.current?.focus();
                            const position = start + emoji.length;
                            composerRef.current?.setSelectionRange(position, position);
                          });
                        }}
                      >
                        <Smile className="size-4" />
                      </button>
                      <label className="cursor-pointer rounded-full p-1.5 hover:bg-secondary" aria-label="Attach file">
                        <Paperclip className="size-4" />
                        <input ref={fileInputRef} type="file" accept="image/*,.pdf,.docx,.zip" className="hidden" onChange={handleAttachmentChange} />
                      </label>
                    </div>
                  </div>
                  {isTyping && <p className="mt-2 text-xs text-muted-foreground">{displayPartner.full_name} is typing...</p>}
                </div>
                <Button onClick={() => void sendMessage()} disabled={isSending || (!text.trim() && !attachmentFile)} size="icon" aria-label="Send message" className="h-[52px] w-[52px] shrink-0 rounded-2xl">
                  <Send className="size-4" />
                </Button>
              </div>
            </div>
          </section>
        ) : (
          <Empty title="Choose a conversation" body="Select someone on the left to view your messages." />
        )}
      </div>
    </>
  );
}
