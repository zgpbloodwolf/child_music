import type { Song, SongMeta } from '@/types/song';
import type { Category, SubCategory } from '@/types/category';
import { RequestError, request } from '@/utils/request';
import type { SearchFilter, SongRepository } from './types';

/**
 * 后端 API Repository:通过网络接口获取曲库数据,替代本地 JsonCatalogRepository。
 *
 * 后端返回的 Song 自带完整网络 URL 的 src/cover(见 server 端 services/meta.build_url),
 * 可直接喂给播放器(audio.ts 对 http(s) 地址直接放行)与图片组件,无需前端再拼接。
 * 列表/搜索类返回 SongMeta(不含 src/lyric),仅 getDetail 返回完整 Song。
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

  /** 按 id 顺序取轻量元数据;后端按 ids 顺序返回。空列表直接返回空数组(免请求)。 */
  async listByIds(ids: string[]): Promise<SongMeta[]> {
    if (ids.length === 0) return [];
    return request<SongMeta[]>({ url: '/api/songs', params: { ids: ids.join(',') } });
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
