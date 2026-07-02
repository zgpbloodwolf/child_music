import type { PoetryAuthor } from '@/types/poetry';
import { songMap } from './songs';
import { songsOfCategory } from './categories';

/**
 * 古诗(poetry)大类的派生数据查询:作者聚合、按作者取作品、朝代推断。
 * 与 songsOfCategory / findSub 同属 data 层派生查询,纯函数、不涉及 UI。
 */

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

/** poetry 大类所有作品(汇总各子分类,去重);模块内部使用 */
function poetrySongIds(): string[] {
  return songsOfCategory('poetry');
}

/**
 * 取某作者在 poetry 大类下的作品 id 列表(保持录入顺序,去重)。
 * @param author 作者名,需与 Song.artist 完全一致
 */
export function songsOfAuthor(author: string): string[] {
  const ids: string[] = [];
  for (const id of poetrySongIds()) {
    const song = songMap[id];
    if (song && song.artist === author && !ids.includes(id)) ids.push(id);
  }
  return ids;
}

/**
 * 推断某作者的朝代(模块内部使用):先查「作者→朝代」映射表,未命中再按其作品的 subCategory 兜底。
 * @returns 如「唐」「宋」;无法判断返回 ''
 */
function dynastyOfAuthor(author: string): string {
  const mapped = POET_DYNASTY_MAP[author];
  if (mapped) return mapped;
  for (const id of songsOfAuthor(author)) {
    const song = songMap[id];
    if (!song || !song.subCategory) continue;
    const dynasty = SUBCAT_DYNASTY_MAP[song.subCategory];
    if (dynasty) return dynasty;
  }
  return '';
}

/** 列出 poetry 大类下所有作者(按作品数倒序,同名聚合) */
export function listPoetryAuthors(): PoetryAuthor[] {
  const map = new Map<string, string[]>();
  for (const id of poetrySongIds()) {
    const song = songMap[id];
    if (!song) continue;
    const list = map.get(song.artist);
    if (list) {
      if (!list.includes(id)) list.push(id);
    } else {
      map.set(song.artist, [id]);
    }
  }
  const authors: PoetryAuthor[] = [];
  for (const [name, songIds] of map) {
    authors.push({
      name,
      songIds,
      count: songIds.length,
      dynasty: dynastyOfAuthor(name),
    });
  }
  return authors.sort((a, b) => b.count - a.count);
}

/** poetry 下出现过的朝代(去重,用于头部朝代标签) */
export function poetryDynasties(): string[] {
  const set: string[] = [];
  for (const author of listPoetryAuthors()) {
    if (author.dynasty && !set.includes(author.dynasty)) set.push(author.dynasty);
  }
  return set;
}
