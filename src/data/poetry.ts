import type { PoetryAuthor } from '@/types/poetry';
import { getRepository } from '@/repository';

/**
 * 古诗(poetry)大类的派生查询:作者聚合与朝代推断。
 * 与 findSub / categoryIdOfSub 同属 data 层派生查询;数据走 Repository(异步),
 * 不直接依赖 songs 模块,便于歌曲数据从数据源加载。
 *
 * 聚合口径:作者 → 作品数的 GROUP BY 由后端完成(Repository.listAuthors),
 * 前端不再拉全量歌曲列表做内存统计。本文件只保留「展示口径」的规则(作者 → 朝代映射)。
 *
 * 注:原先这里还有 songsOfAuthor()(按作者取作品 id),已删除——歌单页现在统一用
 * Repository.listIds({ category: 'poetry', author }) 直取 id 队列,无需本层转发。
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

/** subCategory → 朝代 兜底映射(poetry 大类实际只有 tang300 一个子类) */
const SUBCAT_DYNASTY_MAP: Record<string, string> = {
  'poetry-tang': '唐',
  'poetry-song': '宋',
  tang300: '唐',
};

/**
 * 推断某作者的朝代:先查「作者→朝代」映射表,未命中再按其作品涉及的子分类兜底。
 * 纯函数(接受聚合结果里的子分类 id 列表),避免为了推断朝代去请求作品明细。
 * @returns 如「唐」「宋」;无法判断返回 ''
 */
export function dynastyOf(author: string, subs: string[]): string {
  const mapped = POET_DYNASTY_MAP[author];
  if (mapped) return mapped;
  for (const sub of subs) {
    const dynasty = SUBCAT_DYNASTY_MAP[sub];
    if (dynasty) return dynasty;
  }
  return '';
}

/** 列出 poetry 大类下所有作者(按作品数倒序,同名聚合)。
 * 作品数由后端 GROUP BY 统计,前端只做朝代映射。 */
export async function listPoetryAuthors(): Promise<PoetryAuthor[]> {
  const stats = await repo.listAuthors({ category: 'poetry' });
  return stats.map((s) => ({
    name: s.name,
    count: s.count,
    dynasty: dynastyOf(s.name, s.subs),
  }));
}

/** 从已取到的作者列表推导出现过的朝代(去重,用于头部朝代标签)。
 * 纯函数:调用方已有 authors 时无需再次请求。 */
export function dynastiesOf(authors: PoetryAuthor[]): string[] {
  const set: string[] = [];
  for (const author of authors) {
    if (author.dynasty && !set.includes(author.dynasty)) set.push(author.dynasty);
  }
  return set;
}
