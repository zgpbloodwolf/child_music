import type { Song, SongMeta } from '@/types/song';
import type { Category, SubCategory } from '@/types/category';
import { RequestError, request } from '@/utils/request';
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
 * 实现严格对齐 SongRepository 契约,切换数据源只改 repository/index.ts 的实例化。
 */
export class ApiCatalogRepository implements SongRepository {
  /** 取某首歌完整信息(含 src/lyric);不存在返回 null。404 归一化为 null,其他错误上抛。 */
  async getDetail(id: string): Promise<Song | null> {
    try {
      return await request<Song>({ url: `/api/songs/${encodeURIComponent(id)}` });
    } catch (err) {
      if (err instanceof RequestError && err.statusCode === 404) return null;
      throw err;
    }
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

  /** 仅取 id 列表:GET /api/songs/ids,响应体不含元数据。 */
  async listIds(query?: SongQuery): Promise<string[]> {
    return request<string[]>({
      url: '/api/songs/ids',
      params: {
        category: query?.category,
        sub: query?.subCategory,
        keyword: query?.keyword,
        author: query?.author,
      },
    });
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

  /** 作者聚合统计:GET /api/authors?category=,统计在后端 SQL 聚合完成。 */
  async listAuthors(query?: AuthorQuery): Promise<AuthorStat[]> {
    return request<AuthorStat[]>({
      url: '/api/authors',
      params: { category: query?.category, sub: query?.subCategory },
    });
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

  async getCategories(): Promise<Category[]> {
    return request<Category[]>({ url: '/api/categories' });
  }

  async findSub(subId: string): Promise<SubCategory | null> {
    return request<SubCategory | null>({ url: `/api/subs/${encodeURIComponent(subId)}` });
  }

  async categoryIdOfSub(subId: string): Promise<string | null> {
    const res = await request<{ categoryId: string | null }>({
      url: `/api/subs/${encodeURIComponent(subId)}/category`,
    });
    return res.categoryId;
  }

  /** 预热:触发一次分类树请求建立连接。失败不阻塞,首次查询会自动重试。 */
  async warmup(): Promise<void> {
    try {
      await this.getCategories();
    } catch (err) {
      console.warn('曲库预热失败,将在首次查询时重试:', err);
    }
  }
}
