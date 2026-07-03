import type { Song, SongMeta } from '@/types/song';
import type { Category, SubCategory } from '@/types/category';
import type { SearchFilter, SongRepository } from './types';
import { loadJson } from './loadJson';

/** songs.json 中单首原始记录(不含 category/subCategory,由父级 key 表达) */
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
/** 分类节点的说明信息(自描述:name/icon/desc + count 快照) */
interface CatalogInfo {
  name: string;
  icon?: string;
  desc?: string;
  count?: number;
}
/** 子类节点:{_info, songs} */
interface SubNode {
  _info: CatalogInfo;
  songs: RawEntry[];
}
/** 大类节点:{_info, 各子类} */
interface CatNode {
  _info: CatalogInfo;
  [subId: string]: SubNode | CatalogInfo;
}
/** songs.json 整体:{大类: 大类节点} */
type CatalogFile = Record<string, CatNode>;

/** 把嵌套目录展平为 Song[],从父级 key 补 category/subCategory;跳过各层 _info。 */
function flatten(file: CatalogFile): Song[] {
  const out: Song[] = [];
  for (const category of Object.keys(file)) {
    const catNode = file[category];
    for (const subCategory of Object.keys(catNode)) {
      if (subCategory === '_info') continue;
      const subNode = catNode[subCategory] as SubNode;
      for (const entry of subNode.songs) {
        out.push({ ...entry, category, subCategory });
      }
    }
  }
  return out;
}

/** 从 songs.json 的各层 _info 构建 Category[](分类树结构 + name/desc/icon)。 */
function buildCategories(file: CatalogFile): Category[] {
  const cats: Category[] = [];
  for (const catId of Object.keys(file)) {
    const catNode = file[catId];
    const catInfo = catNode._info;
    const subs: SubCategory[] = [];
    for (const subId of Object.keys(catNode)) {
      if (subId === '_info') continue;
      const subNode = catNode[subId] as SubNode;
      const info = subNode._info;
      subs.push({ id: subId, name: info.name, icon: info.icon, desc: info.desc });
    }
    cats.push({
      id: catId,
      name: catInfo.name,
      icon: catInfo.icon ?? '',
      desc: catInfo.desc ?? '',
      subs,
    });
  }
  return cats;
}

/**
 * JSON 目录 Repository:运行时 fetch `static/data/songs.json` 到内存。
 * 同时承担「歌曲查询」与「分类树查询」—— 分类的 name/desc/icon 也来自 songs.json(单一源),
 * 不再依赖 categories.ts 静态模块。
 *
 * 适用规模:几千~十万首。元数据是「小数据」,全量驻留内存仅几 MB,搜索/筛选毫秒级。
 * 数据作为 static 下独立资源加载,**不进 JS bundle**(面向大规模:曲库增长不影响 bundle)。
 *
 * 预热机制:首次查询内部自动 await warmup,消费侧无需关心时机。
 */
export class JsonCatalogRepository implements SongRepository {
  private songs: Song[] = [];
  private songMap: Record<string, Song> = {};
  private categories: Category[] = [];
  private warmed = false;
  private warmupPromise: Promise<void> | null = null;
  private readonly url = '/static/data/songs.json';

  /** 预热:fetch + parse + 展平歌曲 + 构建分类树。重复调用安全(幂等)。 */
  async warmup(): Promise<void> {
    if (this.warmed) return;
    const file = await loadJson<CatalogFile>(this.url);
    this.songs = flatten(file);
    this.songMap = this.songs.reduce(
      (map, s) => {
        map[s.id] = s;
        return map;
      },
      {} as Record<string, Song>,
    );
    this.categories = buildCategories(file);
    this.warmed = true;
  }

  /** 确保预热完成(未完成则等待)。所有查询入口调用。 */
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

  async listByCategory(category: string): Promise<SongMeta[]> {
    await this.ensure();
    return this.songs.filter((s) => s.category === category);
  }

  async getCategories(): Promise<Category[]> {
    await this.ensure();
    return this.categories;
  }

  async findSub(subId: string): Promise<SubCategory | null> {
    await this.ensure();
    for (const cat of this.categories) {
      const sub = cat.subs.find((s) => s.id === subId);
      if (sub) return sub;
    }
    return null;
  }

  async categoryIdOfSub(subId: string): Promise<string | null> {
    await this.ensure();
    for (const cat of this.categories) {
      if (cat.subs.some((s) => s.id === subId)) return cat.id;
    }
    return null;
  }
}
