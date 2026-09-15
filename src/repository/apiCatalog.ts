import type { Song, SongMeta } from '@/types/song';
import type { Category, SubCategory } from '@/types/category';
import { RequestError, request } from '@/utils/request';
import { LruCache, TtlCache } from './cache';
import type {
  AuthorQuery,
  AuthorStat,
  Page,
  PageResult,
  SearchFilter,
  SongQuery,
  SongRepository,
} from './types';

/**
 * 单次 ids 查询允许携带的 id 个数上限。
 * 上限来自 URL 长度而非后端限制:每个 id 约 19 字符,超过约 100 个就要 2KB 以上
 * querystring,经反向代理(默认 header/URI 缓冲 8KB)有 414 风险,故在此分片。
 */
const IDS_CHUNK = 100;

/**
 * 分类树缓存有效期。分类树近乎静态(仅后台增删分类时变),给较长 TTL:
 * 首页 / 分类面板 / 歌单页 / 启动预热都会要它,缓存后整个会话只请求一次,
 * 后台改动最迟在本时长后生效。
 */
const TTL_CATEGORIES = 5 * 60 * 1000;

/**
 * 查询类结果(作者聚合 / id 队列)的有效期。
 * 取得较短:目标是吸收「来回切页面造成的重复请求」,而非长期缓存。
 */
const TTL_QUERY = 60 * 1000;

/** 歌曲详情缓存条数上限:约等于常用歌单规模,避免整库歌词堆在内存里。 */
const DETAIL_CACHE_MAX = 200;

/** 分类树缓存的 key(全量唯一一份) */
const CATEGORIES_KEY = 'all';

/**
 * 把查询条件序列化成稳定的缓存 key。
 * 字段顺序固定、空值统一成空串,保证「同条件必得同 key」。
 * 参数取 Partial<SongQuery> 以便同时接受 AuthorQuery(仅含分类维度)。
 * 用 \u0001 作分隔符:不会出现在分类 id / 关键词里,避免拼接歧义。
 */
function queryKey(query?: Partial<SongQuery>): string {
  if (!query) return '';
  return [query.category, query.subCategory, query.keyword, query.author]
    .map((v) => v ?? '')
    .join('\u0001');
}

/**
 * 后端 API Repository:通过网络接口获取曲库数据,替代本地 JsonCatalogRepository。
 *
 * 后端返回的 Song 自带完整网络 URL 的 src/cover(见 server 端 services/meta.build_url),
 * 可直接喂给播放器(audio.ts 对 http(s) 地址直接放行)与图片组件,无需前端再拼接。
 * 列表/搜索类返回 SongMeta(不含 src/lyric),仅 getDetail 返回完整 Song。
 *
 * 「统计」一律由后端算好再下发,不在前端拉全量后内存聚合:
 * - 分类各级歌曲数 → getCategories() 的 songCount
 * - 作者作品数     → listAuthors()(后端 GROUP BY)
 * - 任意条件条数   → listPage(query, { number: 1, size: 1 }).total
 *
 * 「拿 id」与「拿元数据」分开:需要完整有序 id 队列时用 listIds()(仅 id),
 * 需要列表内容时用 listPage() 分页取,同一批数据不会传两遍。
 *
 * 「重复请求」在本类内统一收敛(见 cache.ts):
 * - categories / authors / ids 走 TTL 缓存,in-flight 合并并发调用;
 * - detail 走 LRU 限量缓存(切歌会反复访问同一首);
 * - findSub / categoryIdOfSub 直接由缓存的分类树推导,不再单独请求
 *   (分类树本就含全部大类与子类,含空大类,故树内查不到即等价于后端不存在)。
 *
 * 实现严格对齐 SongRepository 契约,切换数据源只改 repository/index.ts 的实例化。
 */
export class ApiCatalogRepository implements SongRepository {
  /** 分类树:首页 / 分类面板 / 歌单页 / 启动预热共用,缓存后整个会话只请求一次 */
  private readonly categoryCache = new TtlCache<Category[]>(TTL_CATEGORIES);
  /** 作者聚合:古诗 tab 来回切换会重复请求同一份聚合结果 */
  private readonly authorCache = new TtlCache<AuthorStat[]>(TTL_QUERY);
  /** id 队列:歌单页退出再进入时查询条件通常相同 */
  private readonly idsCache = new TtlCache<string[]>(TTL_QUERY);
  /** 歌曲详情(含 src/lyric):切歌会反复访问同一首,按 LRU 限量 */
  private readonly detailCache = new LruCache<Song | null>(DETAIL_CACHE_MAX);

  /** 取某首歌完整信息(含 src/lyric);不存在返回 null。404 归一化为 null,其他错误上抛。 */
  async getDetail(id: string): Promise<Song | null> {
    return this.detailCache.get(id, async () => {
      try {
        return await request<Song>({ url: `/api/songs/${encodeURIComponent(id)}` });
      } catch (err) {
        if (err instanceof RequestError && err.statusCode === 404) return null;
        throw err;
      }
    });
  }

  /** 关键词搜索(name/artist/album),可叠加分类过滤。 */
  async search(keyword: string, filter?: SearchFilter): Promise<SongMeta[]> {
    return request<SongMeta[]>({
      url: '/api/songs',
      params: { keyword, category: filter?.category, sub: filter?.subCategory },
    });
  }

  /**
   * 按 id 顺序取轻量元数据;后端按 ids 顺序返回。空列表直接返回空数组(免请求)。
   * 超过 IDS_CHUNK 时分片并发请求后合并,避免长 querystring 触发 414;
   * 分片按序拼接,整体仍保持传入的 id 顺序(后端在 ids 模式下按入参顺序排序)。
   */
  async listByIds(ids: string[]): Promise<SongMeta[]> {
    if (ids.length === 0) return [];
    if (ids.length <= IDS_CHUNK) {
      return request<SongMeta[]>({ url: '/api/songs', params: { ids: ids.join(',') } });
    }
    const chunks: string[][] = [];
    for (let i = 0; i < ids.length; i += IDS_CHUNK) {
      chunks.push(ids.slice(i, i + IDS_CHUNK));
    }
    const parts = await Promise.all(
      chunks.map((chunk) =>
        request<SongMeta[]>({ url: '/api/songs', params: { ids: chunk.join(',') } }),
      ),
    );
    return parts.flat();
  }

  /** 仅取 id 列表:GET /api/songs/ids,响应体不含元数据。同条件结果按 TTL 复用。 */
  async listIds(query?: SongQuery): Promise<string[]> {
    return this.idsCache.get(queryKey(query), () =>
      request<string[]>({
        url: '/api/songs/ids',
        params: {
          category: query?.category,
          sub: query?.subCategory,
          keyword: query?.keyword,
          author: query?.author,
        },
      }),
    );
  }

  /** 分页查询:GET /api/songs?{过滤条件}&page=&size=,返回 items + total。 */
  async listPage(query: SongQuery, page: Page): Promise<PageResult<SongMeta>> {
    return request<PageResult<SongMeta>>({
      url: '/api/songs',
      params: {
        category: query.category,
        sub: query.subCategory,
        keyword: query.keyword,
        author: query.author,
        page: page.number,
        size: page.size,
      },
    });
  }

  /** 作者聚合统计:GET /api/authors?category=,统计在后端 SQL 聚合完成。同条件结果按 TTL 复用。 */
  async listAuthors(query?: AuthorQuery): Promise<AuthorStat[]> {
    return this.authorCache.get(queryKey(query), () =>
      request<AuthorStat[]>({
        url: '/api/authors',
        params: { category: query?.category, sub: query?.subCategory },
      }),
    );
  }

  async listAll(): Promise<SongMeta[]> {
    return request<SongMeta[]>({ url: '/api/songs' });
  }

  async listBySub(subCategory: string): Promise<SongMeta[]> {
    return request<SongMeta[]>({ url: '/api/songs', params: { sub: subCategory } });
  }

  async listByCategory(category: string): Promise<SongMeta[]> {
    return request<SongMeta[]>({ url: '/api/songs', params: { category } });
  }

  /**
   * 取完整分类树。结果按 TTL 缓存,并发调用合并且整个会话通常只请求一次
   * (启动预热的那次请求即填充缓存,后续页面直接命中)。
   */
  async getCategories(): Promise<Category[]> {
    return this.categoryCache.get(CATEGORIES_KEY, () =>
      request<Category[]>({ url: '/api/categories' }),
    );
  }

  /**
   * 按 id 查找子分类。
   *
   * 分类树接口下发全部大类与子类(含空大类),因此树里查得到就等价于后端存在,
   * 查不到即不存在 —— 不再单独请求 /api/subs/{id},与后端语义一致。
   */
  async findSub(subId: string): Promise<SubCategory | null> {
    const cats = await this.getCategories();
    for (const cat of cats) {
      const sub = cat.subs.find((s) => s.id === subId);
      if (sub) return sub;
    }
    return null;
  }

  /** 子分类所属的大类 id。同理由缓存的分类树推导,不单独请求。 */
  async categoryIdOfSub(subId: string): Promise<string | null> {
    const cats = await this.getCategories();
    return cats.find((cat) => cat.subs.some((s) => s.id === subId))?.id ?? null;
  }

  /**
   * 预热:提前请求分类树建立连接,并把结果留在缓存里供后续页面直接命中。
   * 失败不阻塞启动,首次查询会自动重试(失败不进缓存)。
   */
  async warmup(): Promise<void> {
    try {
      await this.getCategories();
    } catch (err) {
      console.warn('曲库预热失败,将在首次查询时重试:', err);
    }
  }
}
