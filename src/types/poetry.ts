/**
 * 古诗(poetry)大类专用类型:作者聚合信息、分类页视图切换模式。
 */

/** 古诗作者聚合信息(由 data/poetry.ts 派生) */
export interface PoetryAuthor {
  /** 作者名,如「李白」 */
  name: string;
  /** 该作者在 poetry 大类下的作品 id 列表 */
  songIds: string[];
  /** 作品数量(= songIds.length,冗余字段便于模板直读) */
  count: number;
  /** 朝代,如「唐」「宋」;无法推断为空字符串 */
  dynasty: string;
}

/** 古诗分类页的内容视图切换模式 */
export enum PoetryViewMode {
  /** 按朝代·类型(默认) */
  BY_TYPE = 'by_type',
  /** 按作者 */
  BY_AUTHOR = 'by_author',
}
