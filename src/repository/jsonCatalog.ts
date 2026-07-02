import type { Song, SongMeta } from '@/types/song';
import type { SearchFilter, SongRepository } from './types';
import { loadJson } from './loadJson';

/** songs.json 中单条原始记录(不含 category/subCategory,由父级 key 表达) */
interface RawEntry {
  id: string;
  name: string;
  artist: string;
  cover: string;
  src: string;
  album?: string;
  duration?: number;
  lyric?: string;
  originalPath?: string;
}
/** songs.json 嵌套结构:{category: {subCategory: [条目]}} */
type RawCatalog = Record<string, Record<string, RawEntry[]>>;

/**
 * 把嵌套目录展平为 Song[],并从父级 key 补回 category / subCategory。
 * originalPath 字段运行时用不到,保留也无害(结构类型允许多余字段)。
 */
function flatten(nested: RawCatalog): Song[] {
  const out: Song[] = [];
  for (const category of Object.keys(nested)) {
    const subs = nested[category];
    for (const subCategory of Object.keys(subs)) {
      for (const entry of subs[subCategory]) {
        out.push({ ...entry, category, subCategory });
      }
    }
  }
  return out;
}

/**
 * JSON 目录 Repository:运行时 fetch `static/data/songs.json` 到内存,展平后查询。
 *
 * 适用规模:几千 ~ 十万首。元数据是「小数据」(每首几百字节),全量驻留内存仅几 MB,
 * 搜索 / 筛选在 JS 数组上是毫秒级。数据作为 static 下独立资源加载,**不进 JS bundle**
 * —— 这是面向大规模数据的核心架构(bundle 不随曲库增长)。
 *
 * 预热机制:首次查询内部自动 await warmup(fetch + parse),消费侧无需关心时机;
 * App onLaunch 可调 warmupRepository() 提前触发,减少首次查询等待。
 */
export class JsonCatalogRepository implements SongRepository {
  private songs: Song[] = [];
  private songMap: Record<string, Song> = {};
  private warmed = false;
  private warmupPromise: Promise<void> | null = null;
  private readonly url = '/static/data/songs.json';

  /** 预热:fetch + parse + 展平到内存。重复调用安全(幂等)。 */
  async warmup(): Promise<void> {
    if (this.warmed) return;
    const nested = await loadJson<RawCatalog>(this.url);
    this.songs = flatten(nested);
    this.songMap = this.songs.reduce(
      (map, s) => {
        map[s.id] = s;
        return map;
      },
      {} as Record<string, Song>,
    );
    this.warmed = true;
  }

  /** 确保预热完成(未完成则等待)。所有查询方法入口调用。 */
  private ensure(): Promise<void> {
    if (this.warmed) return Promise.resolve();
    if (!this.warmupPromise) this.warmupPromise = this.warmup();
    return this.warmupPromise;
  }

  async getDetail(id: string): Promise<Song | null> {
    await this.ensure();
    return this.songMap[id] ?? null;
  }

  async search(keyword: string, filter?: SearchFilter): Promise<SongMeta[]> {
    await this.ensure();
    const kw = keyword.trim().toLowerCase();
    if (!kw) return [];
    return this.songs.filter((s) => {
      const matched =
        s.name.toLowerCase().includes(kw) ||
        s.artist.toLowerCase().includes(kw) ||
        (s.album ?? '').toLowerCase().includes(kw);
      if (!matched) return false;
      if (filter?.category && s.category !== filter.category) return false;
      if (filter?.subCategory && s.subCategory !== filter.subCategory) return false;
      return true;
    });
  }

  async listByIds(ids: string[]): Promise<SongMeta[]> {
    await this.ensure();
    const result: SongMeta[] = [];
    for (const id of ids) {
      const song = this.songMap[id];
      if (song) result.push(song);
    }
    return result;
  }

  async listAll(): Promise<SongMeta[]> {
    await this.ensure();
    return this.songs.slice();
  }

  async listBySub(subCategory: string): Promise<SongMeta[]> {
    await this.ensure();
    return this.songs.filter((s) => s.subCategory === subCategory);
  }
}
