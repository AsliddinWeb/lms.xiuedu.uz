/**
 * useChatSocket — Phase 11b.
 *
 * Chat realtime WebSocket clienti:
 *   - `?token=<access_jwt>` bilan ulanadi
 *   - Avtomatik qayta ulanish (exponential backoff, max 30s)
 *   - Onevent listener ro'yxati (kelgan event'lar pana qiladi)
 *   - `send(event)` — server'ga (typing/ping) yuborish
 *
 * Server tomon (FastAPI) `app/api/v1/communications.py::chat_websocket`.
 */
import { onBeforeUnmount, ref, shallowRef } from 'vue'

import { buildChatWsUrl, type ChatWsEvent } from '@shared/api/chat'
import { TOKEN_KEYS } from '@shared/api/client'

type Listener = (e: ChatWsEvent) => void

export interface ChatSocket {
  connected: ReturnType<typeof ref<boolean>>
  connect: () => void
  disconnect: () => void
  on: (fn: Listener) => () => void
  send: (data: unknown) => void
}

export function useChatSocket(): ChatSocket {
  const connected = ref(false)
  const sock = shallowRef<WebSocket | null>(null)
  const listeners = new Set<Listener>()

  let stopped = false
  let retryMs = 1000
  const maxRetryMs = 30_000
  let reconnectTimer: number | null = null

  function clearReconnect() {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function scheduleReconnect() {
    clearReconnect()
    if (stopped) return
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      doConnect()
    }, retryMs)
    retryMs = Math.min(maxRetryMs, retryMs * 2)
  }

  function doConnect() {
    const token = localStorage.getItem(TOKEN_KEYS.access)
    if (!token) {
      // Token yo'q — uringaymiz, lekin keyinroq qayta urinish
      scheduleReconnect()
      return
    }
    try {
      const ws = new WebSocket(buildChatWsUrl(token))
      sock.value = ws
      ws.onopen = () => {
        connected.value = true
        retryMs = 1000
      }
      ws.onmessage = (ev) => {
        let parsed: ChatWsEvent
        try {
          parsed = JSON.parse(ev.data) as ChatWsEvent
        } catch {
          return
        }
        listeners.forEach((fn) => {
          try {
            fn(parsed)
          } catch (err) {
            console.warn('chat ws listener error', err)
          }
        })
      }
      ws.onerror = () => {
        // onclose ham otiladi — qayta ulanish u yerda
      }
      ws.onclose = () => {
        connected.value = false
        sock.value = null
        if (!stopped) scheduleReconnect()
      }
    } catch (err) {
      console.warn('chat ws connect failed', err)
      scheduleReconnect()
    }
  }

  function connect() {
    stopped = false
    if (sock.value && sock.value.readyState <= WebSocket.OPEN) return
    doConnect()
  }

  function disconnect() {
    stopped = true
    clearReconnect()
    if (sock.value) {
      try {
        sock.value.close()
      } catch {
        // ignore
      }
      sock.value = null
    }
    connected.value = false
  }

  function on(fn: Listener): () => void {
    listeners.add(fn)
    return () => listeners.delete(fn)
  }

  function send(data: unknown): void {
    const ws = sock.value
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(data))
      } catch (err) {
        console.warn('chat ws send failed', err)
      }
    }
  }

  onBeforeUnmount(() => {
    disconnect()
  })

  return { connected, connect, disconnect, on, send }
}
