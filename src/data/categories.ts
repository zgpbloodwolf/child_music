import type { Category, SubCategory } from '@/types/category';

/**
 * 分类树结构定义(对应原型分类页)。
 *
 * 本文件只描述「分类骨架」(大类 / 子分类的 id、名称、图标、描述),**不含歌曲数据**。
 * 歌曲列表由 Repository.listBySub(subId) 运行时异步取 —— 分类结构小且稳定,打包进 bundle;
 * 歌曲数据走 songs.json 不进 bundle(面向大规模数据的核心架构)。
 */

const rawCategories: Category[] = [
  {
    id: 'children',
    name: '儿歌',
    icon: '🎵',
    desc: '欢快活泼,朗朗上口',
    subs: [
      { id: 'children-classic', name: '经典儿歌', icon: '🎶', desc: '传唱多年的经典' },
      { id: 'children-cartoon', name: '动画儿歌', icon: '📺', desc: '动画片主题曲' },
      { id: 'children-lullaby', name: '摇篮曲', icon: '🌙', desc: '哄睡轻柔旋律' },
      { id: 'children-english', name: '英文儿歌', icon: '🔤', desc: '磨耳朵学英语' },
    ],
  },
  {
    id: 'poetry',
    name: '古诗',
    icon: '📜',
    desc: '唐诗宋词,启蒙经典',
    subs: [
      { id: 'poetry-tang', name: '唐诗', icon: '🏯', desc: '李白、杜甫等名家' },
      { id: 'poetry-song', name: '宋词', icon: '🎑', desc: '苏轼、李清照' },
      { id: 'poetry-five', name: '五言绝句', icon: '✋', desc: '二十字的小诗' },
      { id: 'poetry-seven', name: '七言绝句', icon: '7️⃣', desc: '二十八字的小诗' },
    ],
  },
  {
    id: 'classics',
    name: '三字经',
    icon: '📖',
    desc: '国学启蒙经典',
    subs: [
      { id: 'classics-sanzijing', name: '三字经', icon: '📖', desc: '人之初,性本善' },
      { id: 'classics-dizigui', name: '弟子规', icon: '📚', desc: '弟子规,圣人训' },
      { id: 'classics-baijia', name: '百家姓', icon: '📝', desc: '赵钱孙李' },
      { id: 'classics-qianzi', name: '千字文', icon: '📜', desc: '天地玄黄' },
    ],
  },
  {
    id: 'story',
    name: '故事',
    icon: '📚',
    desc: '睡前童话与寓言',
    subs: [
      { id: 'story-fable', name: '寓言故事', icon: '🦊', desc: '小故事大道理' },
      { id: 'story-fairy', name: '童话故事', icon: '🏰', desc: '奇幻的童话世界' },
      { id: 'story-idiom', name: '成语故事', icon: '💡', desc: '学成语懂历史' },
      { id: 'story-myth', name: '神话故事', icon: '🐉', desc: '古老的神话传说' },
    ],
  },
];

export const categories: Category[] = rawCategories;

/** 按 id 建立大类索引 */
export const categoryMap: Record<string, Category> = categories.reduce(
  (map, cat) => {
    map[cat.id] = cat;
    return map;
  },
  {} as Record<string, Category>,
);

/** 按 id 查找子分类 */
export function findSub(subId: string): SubCategory | null {
  for (const cat of categories) {
    const sub = cat.subs.find((s) => s.id === subId);
    if (sub) return sub;
  }
  return null;
}

/** 子分类所属的大类 id(供歌单详情页沿用分类皮肤;无匹配返回 null) */
export function categoryIdOfSub(subId: string): string | null {
  for (const cat of categories) {
    if (cat.subs.some((s) => s.id === subId)) return cat.id;
  }
  return null;
}

// 注:songsOfCategory 已移除 —— 大类歌曲列表由消费方调 Repository.listBySub 各子类汇总。
