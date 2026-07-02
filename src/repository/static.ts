import type { Song, SongMeta } from '@/types/song';
import { songs, songMap } from '@/data/songs';
import type { SearchFilter, SongRepository } from './types';

/**
 * 静态曲库 Repository:基于打包进 bundle 的内存数组(songs / songMap)。
 *
 * 适用规模:数百首。所有方法内部都是同步内存访问,仅用 Promise 包裹以契合
 * SongRepository 的异步契约 —— 这样未来切换到 JsonCatalog / Sqlite
 * (真正的异步 IO)时,消费方代码无需改动。
 *
 * 返回值约定:列表 / 搜索方法返回 SongMeta[](Song 是 SongMeta 的超集,
 * 直接以 Song[] 作为 SongMeta[] 返回,内存中本就是完整对象);仅 getDetail
 * 显式返回完整 Song(含播放所需的 src 与歌词)。
 */
export class StaticRepository implements SongRepository {
  async getDetail(id: string): Promise<Song | null> {
    return songMap[id] ?? null;
  }

  async search(keyword: string, filter?: SearchFilter): Promise<SongMeta[]> {
    const kw = keyword.trim().toLowerCase();
    if (!kw) return [];
    return songs.filter((s) => {
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
    const result: SongMeta[] = [];
    for (const id of ids) {
      const song = songMap[id];
      if (song) result.push(song);
    }
    return result;
  }

  async listAll(): Promise<SongMeta[]> {
    return songs.slice();
  }
}
