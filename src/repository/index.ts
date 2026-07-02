import type { SongRepository } from './types';
import { StaticRepository } from './static';

/**
 * Repository 全局单例入口。
 *
 * 全应用通过 getRepository() 获取曲库数据源,**不直接 import @/data/songs**。
 * 当前返回 StaticRepository;未来按规模在下方切换实例化即可,消费方无感:
 *   数百首 → StaticRepository(当前)
 *   数千首 → JsonCatalogRepository(规划中,按分类 fetch 本地 JSON)
 *   上万首 → SqliteRepository(规划中,查询本地预置数据库)
 */

let instance: SongRepository | null = null;

/** 获取全局 Repository 单例(惰性创建) */
export function getRepository(): SongRepository {
  if (!instance) instance = new StaticRepository();
  return instance;
}

/** 注入自定义实现(仅用于测试,或未来的运行时切换) */
export function setRepository(repo: SongRepository): void {
  instance = repo;
}

export type { SongRepository, SearchFilter, Page, PageResult } from './types';
export type { Song, SongMeta } from '@/types/song';
