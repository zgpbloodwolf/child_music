import type { Category, SubCategory } from '@/types/category';
import { songs, songMap } from './songs';

/**
 * 四大类 → 子分类 的结构定义(对应原型分类页)。
 * songIds 引用 songs.ts 中的歌曲 id;不存在的 id 会被过滤。
 */

/**
 * 按子分类从 songs 自动聚合 id(取代手写 songIds)。
 * 儿歌大类已接入真实资源(239 首),用自动聚合免手写、改分类只动歌曲的 subCategory 即可;
 * 古诗 / 国学 / 故事仍为示例数据,沿用下方手写 songIds。
 */
function idsOfSub(subId: string): string[] {
  return songs.filter((s) => s.subCategory === subId).map((s) => s.id);
}

const rawCategories: Category[] = [
  {
    id: 'children',
    name: '儿歌',
    icon: '🎵',
    desc: '欢快活泼,朗朗上口',
    subs: [
      { id: 'children-classic', name: '经典儿歌', icon: '🎶', desc: '传唱多年的经典', songIds: idsOfSub('children-classic') },
      { id: 'children-cartoon', name: '动画儿歌', icon: '📺', desc: '动画片主题曲', songIds: idsOfSub('children-cartoon') },
      { id: 'children-lullaby', name: '摇篮曲', icon: '🌙', desc: '哄睡轻柔旋律', songIds: idsOfSub('children-lullaby') },
      { id: 'children-english', name: '英文儿歌', icon: '🔤', desc: '磨耳朵学英语', songIds: idsOfSub('children-english') },
    ],
  },
  {
    id: 'poetry',
    name: '古诗',
    icon: '📜',
    desc: '唐诗宋词,启蒙经典',
    subs: [
      { id: 'poetry-tang', name: '唐诗', icon: '🏯', desc: '李白、杜甫等名家', songIds: ['gs001', 'gs002', 'gs003'] },
      { id: 'poetry-song', name: '宋词', icon: '🎑', desc: '苏轼、李清照', songIds: ['gs004', 'gs005'] },
      { id: 'poetry-five', name: '五言绝句', icon: '✋', desc: '二十字的小诗', songIds: ['gs001', 'gs002', 'gs003'] },
      { id: 'poetry-seven', name: '七言绝句', icon: '7️⃣', desc: '二十八字的小诗', songIds: ['gs006', 'gs007'] },
    ],
  },
  {
    id: 'classics',
    name: '三字经',
    icon: '📖',
    desc: '国学启蒙经典',
    subs: [
      { id: 'classics-sanzijing', name: '三字经', icon: '📖', desc: '人之初,性本善', songIds: ['szj001'] },
      { id: 'classics-dizigui', name: '弟子规', icon: '📚', desc: '弟子规,圣人训', songIds: ['dzg001'] },
      { id: 'classics-baijia', name: '百家姓', icon: '📝', desc: '赵钱孙李', songIds: ['bjx001'] },
      { id: 'classics-qianzi', name: '千字文', icon: '📜', desc: '天地玄黄', songIds: ['qzw001'] },
    ],
  },
  {
    id: 'story',
    name: '故事',
    icon: '📚',
    desc: '睡前童话与寓言',
    subs: [
      { id: 'story-fable', name: '寓言故事', icon: '🦊', desc: '小故事大道理', songIds: ['story001', 'story002'] },
      { id: 'story-fairy', name: '童话故事', icon: '🏰', desc: '奇幻的童话世界', songIds: ['story003', 'story004'] },
      { id: 'story-idiom', name: '成语故事', icon: '💡', desc: '学成语懂历史', songIds: ['story005', 'story006'] },
      { id: 'story-myth', name: '神话故事', icon: '🐉', desc: '古老的神话传说', songIds: ['story007', 'story008'] },
    ],
  },
];

/** 过滤掉不存在的歌曲 id 后导出 */
export const categories: Category[] = rawCategories.map((cat) => ({
  ...cat,
  subs: cat.subs.map((sub) => ({
    ...sub,
    songIds: sub.songIds.filter((id) => Boolean(songMap[id])),
  })),
}));

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

/** 获取某大类下所有音频 id(汇总所有子分类,去重) */
export function songsOfCategory(catId: string): string[] {
  const cat = categoryMap[catId];
  if (!cat) return [];
  const ids: string[] = [];
  for (const sub of cat.subs) {
    for (const id of sub.songIds) {
      if (!ids.includes(id)) ids.push(id);
    }
  }
  return ids;
}
