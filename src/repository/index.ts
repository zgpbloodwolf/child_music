import type { SongRepository } from './types';
import { ApiCatalogRepository } from './apiCatalog';

/**
 * Repository 全局单例入口。
 *
 * 当前为 ApiCatalogRepository:曲库元数据走后端服务(经 Nginx Proxy Manager 暴露),
 * 数据**不进 App 包**——音频/封面在线访问(默认),收藏歌曲可下载缓存离线(规划中)。
 * 业务代码通过 getRepository() 取数据源,不直接 import 任何曲库模块,与具体实现解耦。
 *
 * 切换数据源只改此处实例化:ApiCatalog(在线,当前)→ 未来可加离线缓存层。
 * (原 JsonCatalogRepository 保留在文件系统中,作为离线/对比兜底,当前不再启用。)
 */

let instance: SongRepository | null = null;

/** 获取全局 Repository 单例(惰性创建) */
export function getRepository(): SongRepository {
  if (!instance) instance = new ApiCatalogRepository();
  return instance;
}

/** 注入自定义实现(仅用于测试) */
export function setRepository(repo: SongRepository): void {
  instance = repo;
}

/** 启动预热:请求分类树建立连接。查询内部会自动等待预热,故通常无需手动 await。 */
export async function warmupRepository(): Promise<void> {
  await getRepository().warmup?.();
}

export type { SongRepository, SearchFilter, Page, PageResult } from './types';
export type { Song, SongMeta } from '@/types/song';
