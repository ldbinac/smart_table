export class LRUCache<K, V> {
  private cache: Map<K, V>
  private maxSize: number
  
  constructor(maxSize: number = 100) {
    this.cache = new Map()
    this.maxSize = maxSize
  }
  
  get(key: K): V | undefined {
    const value = this.cache.get(key)
    if (value !== undefined) {
      this.cache.delete(key)
      this.cache.set(key, value)
    }
    return value
  }
  
  set(key: K, value: V): void {
    if (this.cache.has(key)) {
      this.cache.delete(key)
    } else if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      if (firstKey !== undefined) {
        this.cache.delete(firstKey)
      }
    }
    this.cache.set(key, value)
  }
  
  has(key: K): boolean {
    return this.cache.has(key)
  }
  
  delete(key: K): boolean {
    return this.cache.delete(key)
  }
  
  clear(): void {
    this.cache.clear()
  }
  
  get size(): number {
    return this.cache.size
  }
  
  keys(): IterableIterator<K> {
    return this.cache.keys()
  }
  
  values(): IterableIterator<V> {
    return this.cache.values()
  }
  
  entries(): IterableIterator<[K, V]> {
    return this.cache.entries()
  }
}

export class TTLCache<K, V> {
  private cache: Map<K, { value: V; expires: number }>
  private defaultTTL: number
  
  constructor(defaultTTL: number = 60000) {
    this.cache = new Map()
    this.defaultTTL = defaultTTL
  }
  
  get(key: K): V | undefined {
    const entry = this.cache.get(key)
    if (!entry) return undefined
    
    if (Date.now() > entry.expires) {
      this.cache.delete(key)
      return undefined
    }
    
    return entry.value
  }
  
  set(key: K, value: V, ttl?: number): void {
    const expires = Date.now() + (ttl ?? this.defaultTTL)
    this.cache.set(key, { value, expires })
  }
  
  has(key: K): boolean {
    const entry = this.cache.get(key)
    if (!entry) return false
    
    if (Date.now() > entry.expires) {
      this.cache.delete(key)
      return false
    }
    
    return true
  }
  
  delete(key: K): boolean {
    return this.cache.delete(key)
  }
  
  clear(): void {
    this.cache.clear()
  }
  
  cleanup(): number {
    const now = Date.now()
    let cleaned = 0
    
    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.expires) {
        this.cache.delete(key)
        cleaned++
      }
    }
    
    return cleaned
  }
  
  get size(): number {
    return this.cache.size
  }
}

export class ComputedCache<K, V> {
  private cache: Map<K, { value: V; dependencies: unknown[] }>
  private compute: (key: K) => { value: V; dependencies: unknown[] }
  
  constructor(
    compute: (key: K) => { value: V; dependencies: unknown[] }
  ) {
    this.cache = new Map()
    this.compute = compute
  }
  
  get(key: K, dependencies?: unknown[]): V {
    const cached = this.cache.get(key)
    
    if (cached && dependencies) {
      const depsChanged = dependencies.length !== cached.dependencies.length ||
        dependencies.some((dep, i) => dep !== cached.dependencies[i])
      
      if (!depsChanged) {
        return cached.value
      }
    }
    
    const result = this.compute(key)
    this.cache.set(key, result)
    
    return result.value
  }
  
  invalidate(key: K): void {
    this.cache.delete(key)
  }
  
  invalidateAll(): void {
    this.cache.clear()
  }
  
  get size(): number {
    return this.cache.size
  }
}

export function createMemoizedSelector<T, R>(
  selector: (state: T) => R,
  isEqual: (a: R, b: R) => boolean = (a, b) => a === b
): (state: T) => R {
  let lastState: T | undefined
  let lastResult: R | undefined
  
  return (state: T): R => {
    if (lastState !== undefined && state === lastState && lastResult !== undefined) {
      return lastResult
    }
    
    const result = selector(state)
    
    if (lastResult !== undefined && isEqual(result, lastResult)) {
      lastState = state
      return lastResult
    }
    
    lastState = state
    lastResult = result
    
    return result
  }
}

export const globalCache = new LRUCache<string, unknown>(1000)

export function getCached<T>(key: string, factory: () => T): T {
  const cached = globalCache.get(key)
  if (cached !== undefined) {
    return cached as T
  }
  
  const value = factory()
  globalCache.set(key, value)
  
  return value
}
