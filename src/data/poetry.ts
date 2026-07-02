import type { PoetryAuthor } from '@/types/poetry';
import type { SongMeta } from '@/types/song';
import { getRepository } from '@/repository';

/**
 * 古诗(poetry)大类的派生查询:作者聚合、按作者取作品、朝代推断。
 * 与 findSub / categoryIdOfSub 同属 data 层派生查询;数据走 Repository(异步),
 * 不直接依赖 songs 模块,便于歌曲数据从 songs.json 加载。
 */

const repo = getRepository();

/** 作者 → 朝代 映射(覆盖仅靠 subCategory 难以推断的作者,如张继仅有「七言绝句」分类) */
const POET_DYNASTY_MAP: Record<string, string> = {
  骆宾王: '唐',
  李白: '唐',
  孟浩然: '唐',
  杜甫: '唐',
  白居易: '唐',
  王维: '唐',
  张继: '唐',
  苏轼: '宋',
  李清照: '宋',
};

/** subCategory → 朝代 兜底映射 */
const SUBCAT_DYNASTY_MAP: Record<string, string> = {
  'poetry-tang': '唐',
  'poetry-song': '宋',
};

/** poetry 大类所有作品(异步,从 repo 取) */
async function poetrySongs(): Promise<SongMeta[]> {
  const all = await repo.listAll();
  return all.filter((s) => s.category === 'poetry');
}

/**
 * 取某作者在 poetry 大类下的作品 id 列表(保持录入顺序,去重)。
 * @param author 作者名,需与 Song.artist 完全一致
 */
export async function songsOfAuthor(author: string): Promise<string[]> {
  const songs = await poetrySongs();
  const ids: string[] = [];
  for (const s of songs) {
    if (s.artist === author && !ids.includes(s.id)) ids.push(s.id);
  }
  return ids;
}

/**
 * 推断某作者的朝代:先查「作者→朝代」映射表,未命中再按其作品的 subCategory 兜底。
 * @returns 如「唐」「宋」;无法判断返回 ''
 */
async function dynastyOfAuthor(author: string): Promise<string> {
  const mapped = POET_DYNASTY_MAP[author];
  if (mapped) return mapped;
  const songs = await poetrySongs();
  for (const s of songs) {
    if (s.artist !== author || !s.subCategory) continue;
    const dynasty = SUBCAT_DYNASTY_MAP[s.subCategory];
    if (dynasty) return dynasty;
  }
  return '';
}

/** 列出 poetry 大类下所有作者(按作品数倒序,同名聚合) */
export async function listPoetryAuthors(): Promise<PoetryAuthor[]> {
  const songs = await poetrySongs();
  const map = new Map<string, string[]>();
  for (const s of songs) {
    const list = map.get(s.artist);
    if (list) {
      if (!list.includes(s.id)) list.push(s.id);
    } else {
      map.set(s.artist, [s.id]);
    }
  }
  const authors: PoetryAuthor[] = [];
  for (const [name, songIds] of map) {
    authors.push({
      name,
      songIds,
      count: songIds.length,
      dynasty: await dynastyOfAuthor(name),
    });
  }
  return authors.sort((a, b) => b.count - a.count);
}

/** poetry 下出现过的朝代(去重,用于头部朝代标签) */
export async function poetryDynasties(): Promise<string[]> {
  const authors = await listPoetryAuthors();
  const set: string[] = [];
  for (const author of authors) {
    if (author.dynasty && !set.includes(author.dynasty)) set.push(author.dynasty);
  }
  return set;
}
