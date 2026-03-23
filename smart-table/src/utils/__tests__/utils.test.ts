import { describe, it, expect } from 'vitest'
import { 
  debounce, 
  throttle, 
  memoize, 
  batch, 
  chunk,
  sleep 
} from '../performance'
import { LRUCache, TTLCache, getCached } from '../cache'

describe('Performance Utils', () => {
  describe('debounce', () => {
    it('should debounce function calls', async () => {
      let callCount = 0
      const fn = debounce(() => callCount++, 100)
      
      fn()
      fn()
      fn()
      
      expect(callCount).toBe(0)
      
      await sleep(150)
      
      expect(callCount).toBe(1)
    })
  })

  describe('throttle', () => {
    it('should throttle function calls', async () => {
      let callCount = 0
      const fn = throttle(() => callCount++, 100)
      
      fn()
      expect(callCount).toBe(1)
      
      fn()
      expect(callCount).toBe(1)
      
      await sleep(150)
      
      fn()
      expect(callCount).toBe(2)
    })
  })

  describe('memoize', () => {
    it('should memoize function results', () => {
      let callCount = 0
      const fn = memoize((...args: unknown[]) => {
        callCount++
        return (args[0] as number) * 2
      })
      
      expect(fn(5)).toBe(10)
      expect(callCount).toBe(1)
      
      expect(fn(5)).toBe(10)
      expect(callCount).toBe(1)
      
      expect(fn(10)).toBe(20)
      expect(callCount).toBe(2)
    })
  })

  describe('batch', () => {
    it('should process items in batches', () => {
      const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
      const results = batch(items, 3, (batch) => batch.reduce((a, b) => a + b, 0))
      
      expect(results).toEqual([6, 15, 24, 10])
    })
  })

  describe('chunk', () => {
    it('should split array into chunks', () => {
      const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
      const chunks = chunk(items, 3)
      
      expect(chunks).toEqual([
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [10]
      ])
    })
  })

  describe('sleep', () => {
    it('should sleep for specified time', async () => {
      const start = Date.now()
      await sleep(100)
      const elapsed = Date.now() - start
      
      expect(elapsed).toBeGreaterThanOrEqual(90)
    })
  })
})

describe('Cache Utils', () => {
  describe('LRUCache', () => {
    it('should store and retrieve values', () => {
      const cache = new LRUCache<string, number>(3)
      
      cache.set('a', 1)
      cache.set('b', 2)
      cache.set('c', 3)
      
      expect(cache.get('a')).toBe(1)
      expect(cache.get('b')).toBe(2)
      expect(cache.get('c')).toBe(3)
    })

    it('should evict least recently used item', () => {
      const cache = new LRUCache<string, number>(2)
      
      cache.set('a', 1)
      cache.set('b', 2)
      cache.set('c', 3)
      
      expect(cache.get('a')).toBeUndefined()
      expect(cache.get('b')).toBe(2)
      expect(cache.get('c')).toBe(3)
    })

    it('should update LRU order on access', () => {
      const cache = new LRUCache<string, number>(2)
      
      cache.set('a', 1)
      cache.set('b', 2)
      cache.get('a')
      cache.set('c', 3)
      
      expect(cache.get('a')).toBe(1)
      expect(cache.get('b')).toBeUndefined()
    })

    it('should check existence', () => {
      const cache = new LRUCache<string, number>(3)
      
      cache.set('a', 1)
      
      expect(cache.has('a')).toBe(true)
      expect(cache.has('b')).toBe(false)
    })

    it('should delete items', () => {
      const cache = new LRUCache<string, number>(3)
      
      cache.set('a', 1)
      cache.delete('a')
      
      expect(cache.has('a')).toBe(false)
    })

    it('should clear all items', () => {
      const cache = new LRUCache<string, number>(3)
      
      cache.set('a', 1)
      cache.set('b', 2)
      cache.clear()
      
      expect(cache.size).toBe(0)
    })
  })

  describe('TTLCache', () => {
    it('should store and retrieve values', () => {
      const cache = new TTLCache<string, number>(1000)
      
      cache.set('a', 1)
      
      expect(cache.get('a')).toBe(1)
    })

    it('should expire values after TTL', async () => {
      const cache = new TTLCache<string, number>(50)
      
      cache.set('a', 1)
      
      expect(cache.get('a')).toBe(1)
      
      await sleep(100)
      
      expect(cache.get('a')).toBeUndefined()
    })

    it('should check existence considering TTL', async () => {
      const cache = new TTLCache<string, number>(50)
      
      cache.set('a', 1)
      
      expect(cache.has('a')).toBe(true)
      
      await sleep(100)
      
      expect(cache.has('a')).toBe(false)
    })
  })

  describe('getCached', () => {
    it('should cache and retrieve values', () => {
      let callCount = 0
      
      const value = getCached('test-key', () => {
        callCount++
        return 42
      })
      
      expect(value).toBe(42)
      expect(callCount).toBe(1)
      
      const cachedValue = getCached('test-key', () => {
        callCount++
        return 99
      })
      
      expect(cachedValue).toBe(42)
      expect(callCount).toBe(1)
    })
  })
})
