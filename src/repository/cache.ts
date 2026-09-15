/**
 * Repository 层的查询缓存:in-flight 去重 + TTL / LRU。
 *
 * 目标只有一个 —— 消除「同一份数据在短时间内被重复请求」,不承担离线缓存职责
 * (离线缓存乃至本地持久化是后续独立一层的事)。两类缓存按生命周期分:
 *
 * - TtlCache:按 key 缓存一段时间。适合 categories / authors / ids 这类
 *   「多个页面都会要、短时间内容易重复请求,且基本不变」的查询。
 * - LruCache:按条数限量、不设过期。适合详情这类「体积大、条目多、但会被
 *   反复访问」的数据,避免整库堆在内存里。
 *
 * 两者都做 in-flight 去重:并发调用同一 key 只真正发一次请求,后来者复用
 * 同一个 Promise;请求失败不写入缓存(后续调用会重新发起)。
 *
 * 约定:缓存内保存的是请求结果的**同一份引用**,调用方只读,不要原地修改
 * 返回值(分类树 / 列表都按只读使用)。
 */

/** 缓存条目 */
interface TtlEntry<T> {
  value: T;
  /** 过期时刻(ms 时间戳) */
  expireAt: number;
}

/** 带过期时间与 in-flight 去重的缓存 */
export class TtlCache<T> {
  private readonly store = new Map<string, TtlEntry<T>>();
  private readonly inflight = new Map<string, Promise<T>>();

  /**
   * @param ttlMs 命中后的有效期(ms)
   * @param maxEntries 条数上限,超限时先清已过期项,再按写入顺序淘汰最旧的
   */
  constructor(
    private readonly ttlMs: number,
    private readonly maxEntries = 64,
  ) {}

  /** 取缓存;未命中或已过期则执行 fetcher。并发同一 key 只执行一次。 */
  async get(key: string, fetcher: () => Promise<T>): Promise<T> {
    const hit = this.store.get(key);
    if (hit && hit.expireAt > Date.now()) return hit.value;

    const pending = this.inflight.get(key);
    if (pending) return pending;

    const task = fetcher()
      .then((value) => {
        this.store.set(key, { value, expireAt: Date.now() + this.ttlMs });
        this.evictIfNeeded();
        return value;
      })
      .finally(() => {
        this.inflight.delete(key);
      });
    this.inflight.set(key, task);
    return task;
  }

  /** 主动失效(如后台改动后需要立即生效时调用) */
  clear(): void {
    this.store.clear();
    this.inflight.clear();
  }

  /** 超限时回收:先清过期项,仍超限则按写入顺序淘汰最旧的 */
  private evictIfNeeded(): void {
    if (this.store.size <= this.maxEntries) return;
    const now = Date.now();
    for (const [key, entry] of this.store) {
      if (entry.expireAt <= now) this.store.delete(key);
    }
    while (this.store.size > this.maxEntries) {
      const oldest = this.store.keys().next().value;
      if (oldest === undefined) break;
      this.store.delete(oldest);
    }
  }
}

/** 按条数限量(最近最少使用优先淘汰)、不设过期时间、带 in-flight 去重的缓存 */
export class LruCache<T> {
  private readonly store = new Map<string, T>();
  private readonly inflight = new Map<string, Promise<T>>();

  /** @param max 条数上限 */
  constructor(private readonly max: number) {}

  /** 取缓存;未命中则执行 fetcher。命中会刷新其「最近使用」次序。 */
  async get(key: string, fetcher: () => Promise<T>): Promise<T> {
    // 用 has 判断:缓存值本身可能就是 null(如 404 归一化结果),不能用真值判断
    if (this.store.has(key)) {
      const value = this.store.get(key) as T;
      this.store.delete(key);
      this.store.set(key, value);
      return value;
    }

    const pending = this.inflight.get(key);
    if (pending) return pending;

    const task = fetcher()
      .then((value) => {
        this.store.set(key, value);
        while (this.store.size > this.max) {
          const oldest = this.store.keys().next().value;
          if (oldest === undefined) break;
          this.store.delete(oldest);
        }
        return value;
      })
      .finally(() => {
        this.inflight.delete(key);
      });
    this.inflight.set(key, task);
    return task;
  }

  /** 主动失效 */
  clear(): void {
    this.store.clear();
    this.inflight.clear();
  }
}
