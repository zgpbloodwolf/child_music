import type { Song, SongMeta } from '@/types/song';
import type { Category, SubCategory } from '@/types/category';

/**
 * Repository(曲库数据源)层的类型与接口契约定义。
 *
 * 设计目标:把「歌曲数据从哪来、怎么查」从业务代码中剥离,让数据源可平滑演进,
 * 而消费方(player / store / 页面)只依赖本接口,切换实现时业务代码无需改动:
 * - ApiCatalogRepository(当前启用):走后端 HTTP 接口,曲库数据不进包
 * - JsonCatalogRepository:fetch 本地 songs.json 到内存,离线兜底(当前未启用)
 *
 * 契约说明:方法均为异步(Promise)。当前静态实现内部为内存数组、几乎立即完成;
 * 未来 JSON / SQLite 实现是真正的异步 IO。消费方一律按异步使用,避免日后返工。
 *
 * ⚠️ 实现可在内部缓存结果(ApiCatalogRepository 即对 categories / detail 等做了
 * TTL 或 LRU 缓存),所以不要假设「每次调用都会发一次请求」;同时缓存返回的是
 * 同一份引用,消费方只读,不要原地修改返回值。
 */

/** 搜索过滤条件(均可选,组合时取交集) */
export interface SearchFilter {
  /** 限定大类,如 'children' / 'poetry' */
  category?: string;
  /** 限定子分类,如 'poetry-tang' */
  subCategory?: string;
}

/** 列表查询条件(均可选,组合时取交集)。比 SearchFilter 多出 keyword / author。 */
export interface SongQuery extends SearchFilter {
  /** 搜索关键词(匹配 name / artist / album) */
  keyword?: string;
  /** 限定作者(精确匹配,如 '李白') */
  author?: string;
}

/** 作者聚合查询条件(与列表过滤口径一致,只用到分类维度) */
export type AuthorQuery = SearchFilter;

/** 作者聚合统计:只含聚合结果,不含作品明细 */
export interface AuthorStat {
  /** 作者名(对应 Song.artist) */
  name: string;
  /** 作品数 */
  count: number;
  /** 作品涉及的子分类 id(供派生的朝代推断等逻辑使用) */
  subs: string[];
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
 *
 * 查询能力的取舍:需要「列表内容 / 服务端分页 / 只要条数」时一律走 listPage
 * (size=1 读 total 即可拿条数);需要「完整有序的 id 队列」时走 listIds。
 * ⚠️ listAll / listBySub / listByCategory 当前已无调用方(仅存契约完整性),
 * 新代码不要再用它们取数。
 */
export interface SongRepository {
  /** 取某首歌的完整信息(含 src / lyric),供播放使用。不存在返回 null。 */
  getDetail(id: string): Promise<Song | null>;
  /** 按关键词搜索(匹配 name / artist / album),可叠加过滤条件。 */
  search(keyword: string, filter?: SearchFilter): Promise<SongMeta[]>;
  /** 按 id 顺序取轻量元数据;自动跳过不存在的 id。 */
  listByIds(ids: string[]): Promise<SongMeta[]>;
  /** 分页查询(支持 category/subCategory/keyword/author 组合);total 可直接用于计数展示。 */
  listPage(query: SongQuery, page: Page): Promise<PageResult<SongMeta>>;
  /**
   * 仅取 id 列表(不含元数据,响应体约为带元数据的 1/10)。
   * 用于需要「完整且有序的 id 队列」的场景(播放入队 + 总数展示);
   * 列表内容请另行用 listPage 分页取,避免同一批数据传两遍。
   */
  listIds(query?: SongQuery): Promise<string[]>;
  /** 按作者聚合统计(作品数 + 涉及子类);统计在后端 GROUP BY 完成,不下拉作品列表。 */
  listAuthors(query?: AuthorQuery): Promise<AuthorStat[]>;
  /** 全部歌曲的轻量元数据。⚠️ 大数据量下应改用 listPage。 */
  listAll(): Promise<SongMeta[]>;
  /** 按子分类取轻量元数据。⚠️ 需要分页/计数时改用 listPage。 */
  listBySub(subCategory: string): Promise<SongMeta[]>;
  /** 按大类取轻量元数据。⚠️ 需要分页/计数时改用 listPage。 */
  listByCategory(category: string): Promise<SongMeta[]>;
  /** 取完整分类树(大类 + 子类,含 name/desc/icon 与各级 songCount,单一源)。 */
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
