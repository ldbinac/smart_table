import type { Socket } from 'socket.io-client'
import type { RealtimeEventMap } from './eventTypes'
import { realtimeEventEmitter } from './eventEmitter'

export interface RealtimeSocketClient {
  connect(): void
  disconnect(): void
  emit<E extends keyof RealtimeEventMap>(event: E, ...args: unknown[]): void
  on<E extends keyof RealtimeEventMap>(event: E, handler: RealtimeEventMap[E]): void
  off<E extends keyof RealtimeEventMap>(event: E, handler: RealtimeEventMap[E]): void
  isConnected(): boolean
}

const INITIAL_RECONNECT_DELAY = 1000
const MAX_RECONNECT_DELAY = 30000

class NullSocketClient implements RealtimeSocketClient {
  connect(): void {}
  disconnect(): void {}
  emit(): void {}
  on(): void {}
  off(): void {}
  isConnected(): boolean {
    return false
  }
}

class SocketClientImpl implements RealtimeSocketClient {
  private socket: Socket | null = null
  private serverUrl: string
  private token: string
  private reconnectAttempts = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private connected = false
  private destroyed = false

  constructor(serverUrl: string, token: string) {
    this.serverUrl = serverUrl
    this.token = token
  }

  async connect(): Promise<void> {
    if (this.socket || this.destroyed) return

    try {
      const { io } = await import('socket.io-client')
      this.socket = io(this.serverUrl, {
        auth: { token: this.token },
        transports: ['websocket', 'polling'],
        reconnection: false,
      })

      this.setupEventHandlers()
    } catch (_e) {
      this.scheduleReconnect()
    }
  }

  private setupEventHandlers(): void {
    if (!this.socket) return

    this.socket.on('connect', () => {
      this.connected = true
      this.reconnectAttempts = 0
      realtimeEventEmitter.emit('connect')
    })

    this.socket.on('disconnect', (reason: string) => {
      this.connected = false
      realtimeEventEmitter.emit('disconnect', reason)
      if (!this.destroyed) {
        this.scheduleReconnect()
      }
    })

    this.socket.on('connect_error', () => {
      this.connected = false
      if (!this.destroyed) {
        this.scheduleReconnect()
      }
    })

    const serverEvents: (keyof RealtimeEventMap)[] = [
      'presence:user_joined',
      'presence:user_left',
      'presence:view_changed',
      'presence:cell_selected',
      'lock:acquired',
      'lock:released',
      'data:record_created',
      'data:record_updated',
      'data:record_deleted',
      'data:field_created',
      'data:field_updated',
      'data:field_deleted',
      'data:view_updated',
      'data:table_created',
      'data:table_updated',
      'data:table_deleted',
    ]

    for (const event of serverEvents) {
      this.socket.on(event as string, (data: unknown) => {
        realtimeEventEmitter.emit(event, data as never)
      })
    }
  }

  private scheduleReconnect(): void {
    if (this.destroyed) return
    if (this.reconnectTimer) return

    const delay = Math.min(
      INITIAL_RECONNECT_DELAY * Math.pow(2, this.reconnectAttempts),
      MAX_RECONNECT_DELAY
    )

    this.reconnectAttempts++

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.attemptReconnect()
    }, delay)
  }

  private async attemptReconnect(): Promise<void> {
    if (this.destroyed || this.connected) return

    if (this.socket) {
      this.socket.removeAllListeners()
      this.socket.disconnect()
      this.socket = null
    }

    await this.connect()
  }

  disconnect(): void {
    this.destroyed = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.socket) {
      this.socket.removeAllListeners()
      this.socket.disconnect()
      this.socket = null
    }
    this.connected = false
    realtimeEventEmitter.removeAllListeners()
  }

  emit<E extends keyof RealtimeEventMap>(event: E, ...args: unknown[]): void {
    if (this.socket && this.connected) {
      this.socket.emit(event as string, ...args)
    }
  }

  on<E extends keyof RealtimeEventMap>(event: E, handler: RealtimeEventMap[E]): void {
    realtimeEventEmitter.on(event, handler as never)
  }

  off<E extends keyof RealtimeEventMap>(event: E, handler: RealtimeEventMap[E]): void {
    realtimeEventEmitter.off(event, handler as never)
  }

  isConnected(): boolean {
    return this.connected
  }
}

export async function createSocketClient(
  serverUrl: string,
  token: string
): Promise<RealtimeSocketClient> {
  if (!serverUrl || !token) {
    return new NullSocketClient()
  }

  try {
    await import('socket.io-client')
    const client = new SocketClientImpl(serverUrl, token)
    return client
  } catch (_e) {
    return new NullSocketClient()
  }
}
