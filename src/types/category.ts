/**
 * 分类(大类 / 子分类)类型定义。
 * 信息架构:大类(Category)→ 子分类(SubCategory)→ 音频(Song)。
 */

/** 子分类(如「唐诗」「寓言故事」) */
export interface SubCategory {
  /** 子分类 id,如 poetry-tang */
  id: string;
  /** 名称,如「唐诗」 */
  name: string;
  /** 图标(emoji,可选) */
  icon?: string;
  /** 描述(可选) */
  desc?: string;
  // 注:歌曲列表不再挂在子分类上,改由 Repository.listBySub(subId) 运行时异步取
}

/** 大类(如「古诗」「故事」) */
export interface Category {
  /** 大类 id:children / poetry / classics / story */
  id: string;
  /** 名称,如「古诗」 */
  name: string;
  /** 图标(emoji) */
  icon: string;
  /** 描述 */
  desc: string;
  /** 该大类下的子分类列表 */
  subs: SubCategory[];
}
