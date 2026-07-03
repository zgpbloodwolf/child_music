import type { Song, SongMeta } from '@/types/song';
import type { Category, SubCategory } from '@/types/category';

/**
 * Repository(曲库数据源)层的类型与接口契约定义。
 *
 * 设计目标:把「歌曲数据从哪来、怎么查」从业务代码中剥离,让数据源可平滑演进,
 * 而消费方(player / store / 页面)只依赖本接口,切换实现时业务代码无需改动:
 * - JsonCatalogRepository 当前实现:运行时 fetch 本地 songs.json 到内存(几百~十万首)
 * - SqliteRepository      规划中:查询本地预置数据库(十万+)
 *
 * 契约说明:方法均为异步(Promise)。当前静态实现内部为内存数组、几乎立即完成;
 * 未来 JSON / SQLite 实现是真正的异步 IO。消费方一律按异步使用,避免日后返工。
 */

/** 搜索过滤条件(均可选,组合时取交集) */
export interface SearchFilter {
  /** 限定大类,如 'children' / 'poetry' */
  category?: string;
  /** 限定子分类,如 'poetry-tang' */
  subCategory?: string;
}

/** 分页请求参数 */
export interface Page {
  /** 页码,从 1 开始 */
  number: number;
  /** 每页条数 */
  size: number;
}

/** 分页结果 */
export interface PageResult<T> {
  items: T[];
  /** 跨页总条数 */
  total: number;
  /** 当前页码 */
  page: number;
  /** 每页条数 */
  pageSize: number;
}

/**
 * 曲库数据源统一接口。
 *
 * 返回值约定:列表 / 搜索类方法返回 SongMeta[](不含 src / lyric,体量小);
 * 仅 getDetail 返回完整 Song(含播放所需的 src 与歌词),供播放器使用。
 */
export interface SongRepository {
  /** 取某首歌的完整信息(含 src / lyric),供播放使用。不存在返回 null。 */
  getDetail(id: string): Promise<Song | null>;
  /** 按关键词搜索(匹配 name / artist / album),可叠加过滤条件。 */
  search(keyword: string, filter?: SearchFilter): Promise<SongMeta[]>;
  /** 按 id 顺序取轻量元数据;自动跳过不存在的 id。 */
  listByIds(ids: string[]): Promise<SongMeta[]>;
  /** 全部歌曲的轻量元数据(首页「全部音频」用)。未来大数据量将改为分页。 */
  listAll(): Promise<SongMeta[]>;
  /** 按子分类取轻量元数据(CategoryPanel / playlist 用)。 */
  listBySub(subCategory: string): Promise<SongMeta[]>;
  /** 取完整分类树(大类 + 子类,含 name/desc/icon;来自 songs.json,单一源)。 */
  getCategories(): Promise<Category[]>;
  /** 按 id 查找子分类。 */
  findSub(subId: string): Promise<SubCategory | null>;
  /** 子分类所属的大类 id(供歌单详情页沿用分类皮肤;无匹配返回 null)。 */
  categoryIdOfSub(subId: string): Promise<string | null>;
  /** 启动预热(仅需 fetch 的实现如 JsonCatalog;静态实现可空操作)。 */
  warmup?(): Promise<void>;
}

// 重新导出基础类型,便于消费方统一从本入口引用(可选)
export type { Song, SongMeta };
