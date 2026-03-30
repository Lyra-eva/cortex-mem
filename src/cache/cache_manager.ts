/**
 * 缓存管理器
 */

export class CacheManager {
  private redisClient: any = null;

  setRedis(redisClient: any) {
    this.redisClient = redisClient;
  }

  async get<T>(key: string): Promise<T | null> {
    if (!this.redisClient) return null;
    try {
      const cached = await this.redisClient.get(key);
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  }

  async set<T>(key: string, value: T, ttl: number): Promise<void> {
    if (!this.redisClient) return;
    try {
      await this.redisClient.setEx(key, ttl, JSON.stringify(value));
    } catch {
      // ignore
    }
  }

  async keys(pattern: string): Promise<string[]> {
    if (!this.redisClient) return [];
    try {
      return await this.redisClient.keys(pattern);
    } catch {
      return [];
    }
  }

  async del(...keys: string[]): Promise<void> {
    if (!this.redisClient || keys.length === 0) return;
    try {
      await this.redisClient.del(...keys);
    } catch {
      // ignore
    }
  }
}

// 全局缓存管理器实例
export const cacheManager = new CacheManager();
