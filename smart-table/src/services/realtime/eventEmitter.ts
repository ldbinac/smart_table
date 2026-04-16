import type { RealtimeEventMap } from './eventTypes'

type EventHandler<T> = T extends () => void
  ? () => void
  : T extends (data: infer D) => void
    ? (data: D) => void
    : never

export class RealtimeEventEmitter {
  private handlers: Map<string, Set<EventHandler<unknown>>> = new Map()

  on<E extends keyof RealtimeEventMap>(event: E, handler: EventHandler<RealtimeEventMap[E]>): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set())
    }
    this.handlers.get(event)!.add(handler as EventHandler<unknown>)
  }

  off<E extends keyof RealtimeEventMap>(event: E, handler: EventHandler<RealtimeEventMap[E]>): void {
    const eventHandlers = this.handlers.get(event)
    if (eventHandlers) {
      eventHandlers.delete(handler as EventHandler<unknown>)
      if (eventHandlers.size === 0) {
        this.handlers.delete(event)
      }
    }
  }

  emit<E extends keyof RealtimeEventMap>(
    event: E,
    ...args: Parameters<RealtimeEventMap[E]>
  ): void {
    const eventHandlers = this.handlers.get(event)
    if (eventHandlers) {
      eventHandlers.forEach((handler) => {
        try {
          ;(handler as (...args: unknown[]) => void)(...args)
        } catch (_e) {
        }
      })
    }
  }

  removeAllListeners(event?: keyof RealtimeEventMap): void {
    if (event) {
      this.handlers.delete(event)
    } else {
      this.handlers.clear()
    }
  }
}

export const realtimeEventEmitter = new RealtimeEventEmitter()
