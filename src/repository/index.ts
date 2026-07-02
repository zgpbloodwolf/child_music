import type { SongRepository } from './types';
import { JsonCatalogRepository } from './jsonCatalog';

/**
 * Repository 全局单例入口。
 *
 * 当前为 JsonCatalogRepository:运行时 fetch `static/data/songs.json` 到内存,
 * 数据**不进 JS bundle**(面向大规模数据的核心架构,曲库增长不影响 bundle/首屏)。
 * 业务代码通过 getRepository() 取数据源,不直接 import 任何曲库模块。
 *
 * 切换数据源只改此处实例化:JsonCatalog(几千~十万首) → SQLite(十万+,规划中)。
 */

let instance: SongRepository | null = null;

/** 获取全局 Repository 单例(惰性创建) */
export function getRepository(): SongRepository {
  if (!instance) instance = new JsonCatalogRepository();
  return instance;
}

/** 注入自定义实现(仅用于测试) */
export function setRepository(repo: SongRepository): void {
  instance = repo;
}

/** 启动预热:fetch songs.json 到内存。查询内部会自动等待预热,故通常无需手动 await。 */
export async function warmupRepository(): Promise<void> {
  await getRepository().warmup?.();
}

export type { SongRepository, SearchFilter, Page, PageResult } from './types';
export type { Song, SongMeta } from '@/types/song';
