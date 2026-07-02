import type { Song } from '@/types/song';

/**
 * 内置曲库数据源(扁平结构)。
 *
 * 本文件含:
 * - 239 首真实儿歌(children 大类,来自 resource 入库,详见 registry/songs-children.json):
 *   音频位于 /static/library/{subCategory}/{id}.mp3,封面同名 .jpg(暂无则由组件色块兜底)。
 * - 古诗 / 国学 / 故事示例数据(占位,后续接入真实资源时替换)。
 *
 * 每首音频标注 category(大类)与 subCategory(主归属子分类);一首音频也可被其他子分类通过 songIds 引用。
 */
export const songs: Song[] = [
  // ===== 儿歌 children =====

  // ----- 动画儿歌 cartoon -----
  { id: 'cn001', name: '阿童木之歌', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn001.jpg', src: '/static/library/children/cartoon/cn001.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn002', name: '爱我你就抱抱我', artist: '经典儿歌', cover: '/static/library/children/classic/cn002.jpg', src: '/static/library/children/classic/cn002.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn003', name: '爸爸妈妈听我说', artist: '经典儿歌', cover: '/static/library/children/classic/cn003.jpg', src: '/static/library/children/classic/cn003.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn004', name: '不倒翁', artist: '经典儿歌', cover: '/static/library/children/classic/cn004.jpg', src: '/static/library/children/classic/cn004.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn005', name: '办家家', artist: '经典儿歌', cover: '/static/library/children/classic/cn005.jpg', src: '/static/library/children/classic/cn005.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn006', name: '拔萝卜', artist: '经典儿歌', cover: '/static/library/children/classic/cn006.jpg', src: '/static/library/children/classic/cn006.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn007', name: '白龙马', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn007.jpg', src: '/static/library/children/cartoon/cn007.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn008', name: '虫儿飞', artist: '经典儿歌', cover: '/static/library/children/classic/cn008.jpg', src: '/static/library/children/classic/cn008.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn009', name: '聪明的一休', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn009.jpg', src: '/static/library/children/cartoon/cn009.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn010', name: '采蘑菇的小姑娘', artist: '经典儿歌', cover: '/static/library/children/classic/cn010.jpg', src: '/static/library/children/classic/cn010.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn011', name: '春天的脚步', artist: '经典儿歌', cover: '/static/library/children/classic/cn011.jpg', src: '/static/library/children/classic/cn011.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn012', name: '春天在哪里', artist: '经典儿歌', cover: '/static/library/children/classic/cn012.jpg', src: '/static/library/children/classic/cn012.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn013', name: '粗心的小画家', artist: '经典儿歌', cover: '/static/library/children/classic/cn013.jpg', src: '/static/library/children/classic/cn013.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn014', name: '打电话', artist: '经典儿歌', cover: '/static/library/children/classic/cn014.jpg', src: '/static/library/children/classic/cn014.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn015', name: '大风车儿歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn015.jpg', src: '/static/library/children/classic/cn015.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn016', name: '嘀哩嘀哩', artist: '经典儿歌', cover: '/static/library/children/classic/cn016.jpg', src: '/static/library/children/classic/cn016.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn017', name: '丢手绢', artist: '经典儿歌', cover: '/static/library/children/classic/cn017.jpg', src: '/static/library/children/classic/cn017.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn018', name: '读书郎', artist: '经典儿歌', cover: '/static/library/children/classic/cn018.jpg', src: '/static/library/children/classic/cn018.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn019', name: '大手牵小手', artist: '经典儿歌', cover: '/static/library/children/classic/cn019.jpg', src: '/static/library/children/classic/cn019.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn020', name: '冬天到', artist: '经典儿歌', cover: '/static/library/children/classic/cn020.jpg', src: '/static/library/children/classic/cn020.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn021', name: '大王叫我来巡山', artist: '经典儿歌', cover: '/static/library/children/classic/cn021.jpg', src: '/static/library/children/classic/cn021.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn022', name: '当我们在一起', artist: '经典儿歌', cover: '/static/library/children/classic/cn022.jpg', src: '/static/library/children/classic/cn022.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn023', name: 'DO RE MI', artist: '经典儿歌', cover: '/static/library/children/classic/cn023.jpg', src: '/static/library/children/classic/cn023.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn024', name: '放风筝', artist: '经典儿歌', cover: '/static/library/children/classic/cn024.jpg', src: '/static/library/children/classic/cn024.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn025', name: '共产儿童团歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn025.jpg', src: '/static/library/children/classic/cn025.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn026', name: '歌唱二小放牛郎', artist: '经典儿歌', cover: '/static/library/children/classic/cn026.jpg', src: '/static/library/children/classic/cn026.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn027', name: '歌唱祖国', artist: '经典儿歌', cover: '/static/library/children/classic/cn027.jpg', src: '/static/library/children/classic/cn027.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn028', name: '歌声与微笑', artist: '经典儿歌', cover: '/static/library/children/classic/cn028.jpg', src: '/static/library/children/classic/cn028.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn029', name: '恭喜恭喜', artist: '经典儿歌', cover: '/static/library/children/classic/cn029.jpg', src: '/static/library/children/classic/cn029.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn030', name: '葫芦娃', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn030.jpg', src: '/static/library/children/cartoon/cn030.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn031', name: '好阿姨', artist: '经典儿歌', cover: '/static/library/children/classic/cn031.jpg', src: '/static/library/children/classic/cn031.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn032', name: '好宝宝', artist: '经典儿歌', cover: '/static/library/children/classic/cn032.jpg', src: '/static/library/children/classic/cn032.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn033', name: '好爸爸坏爸爸', artist: '经典儿歌', cover: '/static/library/children/classic/cn033.jpg', src: '/static/library/children/classic/cn033.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn034', name: '蝴蝶', artist: '经典儿歌', cover: '/static/library/children/classic/cn034.jpg', src: '/static/library/children/classic/cn034.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn035', name: '好好吃饭', artist: '经典儿歌', cover: '/static/library/children/classic/cn035.jpg', src: '/static/library/children/classic/cn035.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn036', name: '黑猫警长', artist: '安安', cover: '/static/library/children/cartoon/cn036.jpg', src: '/static/library/children/cartoon/cn036.mp3', category: 'children', subCategory: 'children-cartoon' },
  { id: 'cn037', name: '黑猫警长', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn037.jpg', src: '/static/library/children/cartoon/cn037.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn038', name: '好妈妈', artist: '经典儿歌', cover: '/static/library/children/classic/cn038.jpg', src: '/static/library/children/classic/cn038.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn039', name: '红星歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn039.jpg', src: '/static/library/children/classic/cn039.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn040', name: '花仙子之歌', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn040.jpg', src: '/static/library/children/cartoon/cn040.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn041', name: '花与蝶', artist: '经典儿歌', cover: '/static/library/children/classic/cn041.jpg', src: '/static/library/children/classic/cn041.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn042', name: '花园里的洋娃娃', artist: '经典儿歌', cover: '/static/library/children/classic/cn042.jpg', src: '/static/library/children/classic/cn042.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn043', name: '机器猫', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn043.jpg', src: '/static/library/children/cartoon/cn043.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn044', name: '健康歌', artist: '小薇薇', cover: '/static/library/children/classic/cn044.jpg', src: '/static/library/children/classic/cn044.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn045', name: '吉祥三宝', artist: '经典儿歌', cover: '/static/library/children/classic/cn045.jpg', src: '/static/library/children/classic/cn045.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn046', name: '快乐小鱼', artist: '经典儿歌', cover: '/static/library/children/classic/cn046.jpg', src: '/static/library/children/classic/cn046.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn047', name: '夸我是个好孩子', artist: '经典儿歌', cover: '/static/library/children/classic/cn047.jpg', src: '/static/library/children/classic/cn047.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn048', name: '伦敦铁桥垮下来', artist: '经典儿歌', cover: '/static/library/children/classic/cn048.jpg', src: '/static/library/children/classic/cn048.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn049', name: '懒惰虫', artist: '经典儿歌', cover: '/static/library/children/classic/cn049.jpg', src: '/static/library/children/classic/cn049.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn050', name: '鲁冰花', artist: '经典儿歌', cover: '/static/library/children/classic/cn050.jpg', src: '/static/library/children/classic/cn050.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn051', name: '劳动最光荣', artist: '经典儿歌', cover: '/static/library/children/classic/cn051.jpg', src: '/static/library/children/classic/cn051.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn052', name: '铃儿响叮当', artist: '经典儿歌', cover: '/static/library/children/classic/cn052.jpg', src: '/static/library/children/classic/cn052.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn053', name: '兰花草', artist: '经典儿歌', cover: '/static/library/children/classic/cn053.jpg', src: '/static/library/children/classic/cn053.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn054', name: '蓝精灵', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn054.jpg', src: '/static/library/children/cartoon/cn054.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn055', name: '老鸡带小鸡', artist: '经典儿歌', cover: '/static/library/children/classic/cn055.jpg', src: '/static/library/children/classic/cn055.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn056', name: '拉拉勾勾', artist: '经典儿歌', cover: '/static/library/children/classic/cn056.jpg', src: '/static/library/children/classic/cn056.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn057', name: '狼来了', artist: '经典儿歌', cover: '/static/library/children/classic/cn057.jpg', src: '/static/library/children/classic/cn057.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn058', name: '老母鸡', artist: '经典儿歌', cover: '/static/library/children/classic/cn058.jpg', src: '/static/library/children/classic/cn058.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn059', name: '雷欧之歌', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn059.jpg', src: '/static/library/children/cartoon/cn059.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn060', name: '老鹰抓小鸡', artist: '经典儿歌', cover: '/static/library/children/classic/cn060.jpg', src: '/static/library/children/classic/cn060.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn061', name: '两只老虎', artist: '经典儿歌', cover: '/static/library/children/classic/cn061.jpg', src: '/static/library/children/classic/cn061.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn062', name: '两只小象', artist: '经典儿歌', cover: '/static/library/children/classic/cn062.jpg', src: '/static/library/children/classic/cn062.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn063', name: '卖报歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn063.jpg', src: '/static/library/children/classic/cn063.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn064', name: '蜜蜂做工', artist: '经典儿歌', cover: '/static/library/children/classic/cn064.jpg', src: '/static/library/children/classic/cn064.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn065', name: '卖花姑娘', artist: '经典儿歌', cover: '/static/library/children/classic/cn065.jpg', src: '/static/library/children/classic/cn065.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn066', name: '迷路的小花鸭', artist: '经典儿歌', cover: '/static/library/children/classic/cn066.jpg', src: '/static/library/children/classic/cn066.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn067', name: '茉莉花', artist: '经典儿歌', cover: '/static/library/children/classic/cn067.jpg', src: '/static/library/children/classic/cn067.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn068', name: '木马', artist: '经典儿歌', cover: '/static/library/children/classic/cn068.jpg', src: '/static/library/children/classic/cn068.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn069', name: '妈妈的吻', artist: '经典儿歌', cover: '/static/library/children/classic/cn069.jpg', src: '/static/library/children/classic/cn069.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn070', name: '卖汤圆', artist: '经典儿歌', cover: '/static/library/children/classic/cn070.jpg', src: '/static/library/children/classic/cn070.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn071', name: '泥娃娃', artist: '经典儿歌', cover: '/static/library/children/classic/cn071.jpg', src: '/static/library/children/classic/cn071.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn072', name: '拍拍手好朋友', artist: '经典儿歌', cover: '/static/library/children/classic/cn072.jpg', src: '/static/library/children/classic/cn072.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn073', name: '拍手游戏', artist: '经典儿歌', cover: '/static/library/children/classic/cn073.jpg', src: '/static/library/children/classic/cn073.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn074', name: '雀尕飞', artist: '经典儿歌', cover: '/static/library/children/classic/cn074.jpg', src: '/static/library/children/classic/cn074.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn075', name: '青春舞曲', artist: '经典儿歌', cover: '/static/library/children/classic/cn075.jpg', src: '/static/library/children/classic/cn075.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn076', name: '青苹果乐园', artist: '经典儿歌', cover: '/static/library/children/classic/cn076.jpg', src: '/static/library/children/classic/cn076.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn077', name: '亲亲我', artist: '经典儿歌', cover: '/static/library/children/classic/cn077.jpg', src: '/static/library/children/classic/cn077.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn078', name: '亲亲猪猪宝贝', artist: '经典儿歌', cover: '/static/library/children/classic/cn078.jpg', src: '/static/library/children/classic/cn078.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn079', name: '秋天来了', artist: '经典儿歌', cover: '/static/library/children/classic/cn079.jpg', src: '/static/library/children/classic/cn079.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn080', name: '青蛙跳', artist: '经典儿歌', cover: '/static/library/children/classic/cn080.jpg', src: '/static/library/children/classic/cn080.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn081', name: '七子之歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn081.jpg', src: '/static/library/children/classic/cn081.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn082', name: '让我们荡起双桨', artist: '经典儿歌', cover: '/static/library/children/classic/cn082.jpg', src: '/static/library/children/classic/cn082.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn083', name: '上学歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn083.jpg', src: '/static/library/children/classic/cn083.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn084', name: '手指歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn084.jpg', src: '/static/library/children/classic/cn084.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn085', name: '圣诞铃声', artist: '经典儿歌', cover: '/static/library/children/classic/cn085.jpg', src: '/static/library/children/classic/cn085.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn086', name: '三个和尚', artist: '经典儿歌', cover: '/static/library/children/classic/cn086.jpg', src: '/static/library/children/classic/cn086.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn087', name: '数蛤蟆', artist: '经典儿歌', cover: '/static/library/children/classic/cn087.jpg', src: '/static/library/children/classic/cn087.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn088', name: '水龙头', artist: '经典儿歌', cover: '/static/library/children/classic/cn088.jpg', src: '/static/library/children/classic/cn088.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn089', name: '少年英雄小哪吒', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn089.jpg', src: '/static/library/children/cartoon/cn089.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn090', name: '生日快乐', artist: '经典儿歌', cover: '/static/library/children/classic/cn090.jpg', src: '/static/library/children/classic/cn090.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn091', name: '世上只有妈妈好', artist: '经典儿歌', cover: '/static/library/children/classic/cn091.jpg', src: '/static/library/children/classic/cn091.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn092', name: '随它吧', artist: '胡维纳', cover: '/static/library/children/cartoon/cn092.jpg', src: '/static/library/children/cartoon/cn092.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn093', name: '数鸭子', artist: '经典儿歌', cover: '/static/library/children/classic/cn093.jpg', src: '/static/library/children/classic/cn093.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn094', name: '兔子舞', artist: '经典儿歌', cover: '/static/library/children/classic/cn094.jpg', src: '/static/library/children/classic/cn094.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn095', name: '无敌小可爱', artist: '经典儿歌', cover: '/static/library/children/classic/cn095.jpg', src: '/static/library/children/classic/cn095.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn096', name: '我爱北京天安门', artist: '经典儿歌', cover: '/static/library/children/classic/cn096.jpg', src: '/static/library/children/classic/cn096.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn097', name: '我爱我的小动物', artist: '经典儿歌', cover: '/static/library/children/classic/cn097.jpg', src: '/static/library/children/classic/cn097.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn098', name: '我爱我的幼儿园', artist: '经典儿歌', cover: '/static/library/children/classic/cn098.jpg', src: '/static/library/children/classic/cn098.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn099', name: '我的朋友在哪里', artist: '经典儿歌', cover: '/static/library/children/classic/cn099.jpg', src: '/static/library/children/classic/cn099.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn100', name: '我的小宝宝', artist: '经典儿歌', cover: '/static/library/children/classic/cn100.jpg', src: '/static/library/children/classic/cn100.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn101', name: '哇哈哈', artist: '经典儿歌', cover: '/static/library/children/classic/cn101.jpg', src: '/static/library/children/classic/cn101.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn102', name: '娃哈哈', artist: '经典儿歌', cover: '/static/library/children/classic/cn102.jpg', src: '/static/library/children/classic/cn102.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn103', name: '我还有点小糊涂', artist: '经典儿歌', cover: '/static/library/children/classic/cn103.jpg', src: '/static/library/children/classic/cn103.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn104', name: '玩具国', artist: '经典儿歌', cover: '/static/library/children/classic/cn104.jpg', src: '/static/library/children/classic/cn104.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn105', name: '我们都是小青蛙', artist: '经典儿歌', cover: '/static/library/children/classic/cn105.jpg', src: '/static/library/children/classic/cn105.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn106', name: '我们的田野', artist: '经典儿歌', cover: '/static/library/children/classic/cn106.jpg', src: '/static/library/children/classic/cn106.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn107', name: '玩泥巴', artist: '经典儿歌', cover: '/static/library/children/classic/cn107.jpg', src: '/static/library/children/classic/cn107.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn108', name: '蜗牛与黄鹂鸟', artist: '经典儿歌', cover: '/static/library/children/classic/cn108.jpg', src: '/static/library/children/classic/cn108.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn109', name: '外婆的澎湖湾', artist: '经典儿歌', cover: '/static/library/children/classic/cn109.jpg', src: '/static/library/children/classic/cn109.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn110', name: '我是好宝宝', artist: '经典儿歌', cover: '/static/library/children/classic/cn110.jpg', src: '/static/library/children/classic/cn110.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn111', name: '小篱笆', artist: '经典儿歌', cover: '/static/library/children/classic/cn111.jpg', src: '/static/library/children/classic/cn111.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn112', name: '小螺号', artist: '经典儿歌', cover: '/static/library/children/classic/cn112.jpg', src: '/static/library/children/classic/cn112.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn113', name: '雪宝宝', artist: '经典儿歌', cover: '/static/library/children/classic/cn113.jpg', src: '/static/library/children/classic/cn113.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn114', name: '小白兔白又白', artist: '经典儿歌', cover: '/static/library/children/classic/cn114.jpg', src: '/static/library/children/classic/cn114.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn115', name: '小白兔乖乖', artist: '经典儿歌', cover: '/static/library/children/classic/cn115.jpg', src: '/static/library/children/classic/cn115.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn116', name: '小草', artist: '经典儿歌', cover: '/static/library/children/classic/cn116.jpg', src: '/static/library/children/classic/cn116.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn117', name: '下池塘', artist: '经典儿歌', cover: '/static/library/children/classic/cn117.jpg', src: '/static/library/children/classic/cn117.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn118', name: '小二郎上学', artist: '经典儿歌', cover: '/static/library/children/classic/cn118.jpg', src: '/static/library/children/classic/cn118.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn119', name: '幸福拍手歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn119.jpg', src: '/static/library/children/classic/cn119.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn120', name: '小红花', artist: '经典儿歌', cover: '/static/library/children/classic/cn120.jpg', src: '/static/library/children/classic/cn120.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn121', name: '小红帽', artist: '经典儿歌', cover: '/static/library/children/classic/cn121.jpg', src: '/static/library/children/classic/cn121.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn122', name: '小花猫', artist: '经典儿歌', cover: '/static/library/children/classic/cn122.jpg', src: '/static/library/children/classic/cn122.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn123', name: '小机灵之歌', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn123.jpg', src: '/static/library/children/cartoon/cn123.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn124', name: '香蕉梨', artist: '经典儿歌', cover: '/static/library/children/classic/cn124.jpg', src: '/static/library/children/classic/cn124.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn125', name: '小老鼠', artist: '经典儿歌', cover: '/static/library/children/classic/cn125.jpg', src: '/static/library/children/classic/cn125.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn126', name: '小老鼠上灯台', artist: '经典儿歌', cover: '/static/library/children/classic/cn126.jpg', src: '/static/library/children/classic/cn126.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn127', name: '小猫', artist: '经典儿歌', cover: '/static/library/children/classic/cn127.jpg', src: '/static/library/children/classic/cn127.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn128', name: '小毛驴', artist: '经典儿歌', cover: '/static/library/children/classic/cn128.jpg', src: '/static/library/children/classic/cn128.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn129', name: '小蚂蚁', artist: '经典儿歌', cover: '/static/library/children/classic/cn129.jpg', src: '/static/library/children/classic/cn129.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn130', name: '小免子乖乖', artist: '经典儿歌', cover: '/static/library/children/classic/cn130.jpg', src: '/static/library/children/classic/cn130.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn131', name: '小手拍拍', artist: '经典儿歌', cover: '/static/library/children/classic/cn131.jpg', src: '/static/library/children/classic/cn131.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn132', name: '小松鼠', artist: '经典儿歌', cover: '/static/library/children/classic/cn132.jpg', src: '/static/library/children/classic/cn132.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn133', name: '小兔子乖乖', artist: '经典儿歌', cover: '/static/library/children/classic/cn133.jpg', src: '/static/library/children/classic/cn133.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn134', name: '小星星', artist: '经典儿歌', cover: '/static/library/children/classic/cn134.jpg', src: '/static/library/children/classic/cn134.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn135', name: '小小雨点', artist: '经典儿歌', cover: '/static/library/children/classic/cn135.jpg', src: '/static/library/children/classic/cn135.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn136', name: '小燕子', artist: '经典儿歌', cover: '/static/library/children/classic/cn136.jpg', src: '/static/library/children/classic/cn136.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn137', name: '小竹笋', artist: '经典儿歌', cover: '/static/library/children/classic/cn137.jpg', src: '/static/library/children/classic/cn137.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn138', name: '小猪吃得饱饱', artist: '经典儿歌', cover: '/static/library/children/classic/cn138.jpg', src: '/static/library/children/classic/cn138.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn139', name: '小猪睡觉', artist: '经典儿歌', cover: '/static/library/children/classic/cn139.jpg', src: '/static/library/children/classic/cn139.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 摇篮曲 lullaby -----
  { id: 'cn140', name: '摇啊摇', artist: '经典儿歌', cover: '/static/library/children/lullaby/cn140.jpg', src: '/static/library/children/lullaby/cn140.mp3', category: 'children', subCategory: 'children-lullaby' },

  // ----- 经典儿歌 classic -----
  { id: 'cn141', name: '伊比呀呀', artist: '经典儿歌', cover: '/static/library/children/classic/cn141.jpg', src: '/static/library/children/classic/cn141.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn142', name: '一二三数字歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn142.jpg', src: '/static/library/children/classic/cn142.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn143', name: '幼儿园里朋友多', artist: '经典儿歌', cover: '/static/library/children/classic/cn143.jpg', src: '/static/library/children/classic/cn143.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn144', name: '一分钱', artist: '经典儿歌', cover: '/static/library/children/classic/cn144.jpg', src: '/static/library/children/classic/cn144.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn145', name: '一个师傅三徒弟', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn145.jpg', src: '/static/library/children/cartoon/cn145.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn146', name: '萤火虫', artist: '经典儿歌', cover: '/static/library/children/classic/cn146.jpg', src: '/static/library/children/classic/cn146.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn147', name: '音阶歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn147.jpg', src: '/static/library/children/classic/cn147.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn148', name: '颜色歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn148.jpg', src: '/static/library/children/classic/cn148.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn149', name: '洋娃娃和熊跳舞', artist: '经典儿歌', cover: '/static/library/children/classic/cn149.jpg', src: '/static/library/children/classic/cn149.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 动画儿歌 cartoon -----
  { id: 'cn150', name: '一休和尚', artist: '经典儿歌', cover: '/static/library/children/cartoon/cn150.jpg', src: '/static/library/children/cartoon/cn150.mp3', category: 'children', subCategory: 'children-cartoon' },

  // ----- 经典儿歌 classic -----
  { id: 'cn151', name: '一只哈巴狗', artist: '经典儿歌', cover: '/static/library/children/classic/cn151.jpg', src: '/static/library/children/classic/cn151.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn152', name: '找爸爸', artist: '经典儿歌', cover: '/static/library/children/classic/cn152.jpg', src: '/static/library/children/classic/cn152.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn153', name: '祖国的花朵', artist: '经典儿歌', cover: '/static/library/children/classic/cn153.jpg', src: '/static/library/children/classic/cn153.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn154', name: '中国少年先锋队队歌', artist: '经典儿歌', cover: '/static/library/children/classic/cn154.jpg', src: '/static/library/children/classic/cn154.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn155', name: '卓玛', artist: '经典儿歌', cover: '/static/library/children/classic/cn155.jpg', src: '/static/library/children/classic/cn155.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn156', name: '在哪里', artist: '经典儿歌', cover: '/static/library/children/classic/cn156.jpg', src: '/static/library/children/classic/cn156.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn157', name: '找朋友', artist: '经典儿歌', cover: '/static/library/children/classic/cn157.jpg', src: '/static/library/children/classic/cn157.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn158', name: '种太阳', artist: '经典儿歌', cover: '/static/library/children/classic/cn158.jpg', src: '/static/library/children/classic/cn158.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn159', name: '猪小弟', artist: '经典儿歌', cover: '/static/library/children/classic/cn159.jpg', src: '/static/library/children/classic/cn159.mp3', category: 'children', subCategory: 'children-classic' },
  { id: 'cn160', name: '做游戏', artist: '经典儿歌', cover: '/static/library/children/classic/cn160.jpg', src: '/static/library/children/classic/cn160.mp3', category: 'children', subCategory: 'children-classic' },

  // ----- 英文儿歌 english -----
  { id: 'en001', name: '保护环境', artist: '早教英语', cover: '/static/library/children/english/en001.jpg', src: '/static/library/children/english/en001.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en002', name: '参观牧场', artist: '早教英语', cover: '/static/library/children/english/en002.jpg', src: '/static/library/children/english/en002.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en003', name: '春夏秋冬', artist: '早教英语', cover: '/static/library/children/english/en003.jpg', src: '/static/library/children/english/en003.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en004', name: '大自然', artist: '早教英语', cover: '/static/library/children/english/en004.jpg', src: '/static/library/children/english/en004.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en005', name: '海洋动物', artist: '早教英语', cover: '/static/library/children/english/en005.jpg', src: '/static/library/children/english/en005.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en006', name: '家具用品', artist: '早教英语', cover: '/static/library/children/english/en006.jpg', src: '/static/library/children/english/en006.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en007', name: '家用电器', artist: '早教英语', cover: '/static/library/children/english/en007.jpg', src: '/static/library/children/english/en007.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en008', name: '讲卫生', artist: '早教英语', cover: '/static/library/children/english/en008.jpg', src: '/static/library/children/english/en008.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en009', name: '交通工具', artist: '早教英语', cover: '/static/library/children/english/en009.jpg', src: '/static/library/children/english/en009.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en010', name: '介绍职业', artist: '早教英语', cover: '/static/library/children/english/en010.jpg', src: '/static/library/children/english/en010.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en011', name: '快乐一周', artist: '早教英语', cover: '/static/library/children/english/en011.jpg', src: '/static/library/children/english/en011.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en012', name: '礼貌用语', artist: '早教英语', cover: '/static/library/children/english/en012.jpg', src: '/static/library/children/english/en012.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en013', name: '拍手游戏', artist: '早教英语', cover: '/static/library/children/english/en013.jpg', src: '/static/library/children/english/en013.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en014', name: '去上学', artist: '早教英语', cover: '/static/library/children/english/en014.jpg', src: '/static/library/children/english/en014.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en015', name: '人体五官', artist: '早教英语', cover: '/static/library/children/english/en015.jpg', src: '/static/library/children/english/en015.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en016', name: '认识昆虫', artist: '早教英语', cover: '/static/library/children/english/en016.jpg', src: '/static/library/children/english/en016.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en017', name: '认识鸟类', artist: '早教英语', cover: '/static/library/children/english/en017.jpg', src: '/static/library/children/english/en017.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en018', name: '认识食物', artist: '早教英语', cover: '/static/library/children/english/en018.jpg', src: '/static/library/children/english/en018.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en019', name: '认识天气', artist: '早教英语', cover: '/static/library/children/english/en019.jpg', src: '/static/library/children/english/en019.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en020', name: '认识文具', artist: '早教英语', cover: '/static/library/children/english/en020.jpg', src: '/static/library/children/english/en020.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en021', name: '认识字母', artist: '早教英语', cover: '/static/library/children/english/en021.jpg', src: '/static/library/children/english/en021.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en022', name: '淘气宝宝', artist: '早教英语', cover: '/static/library/children/english/en022.jpg', src: '/static/library/children/english/en022.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en023', name: '体育运动', artist: '早教英语', cover: '/static/library/children/english/en023.jpg', src: '/static/library/children/english/en023.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en024', name: '我的家庭', artist: '早教英语', cover: '/static/library/children/english/en024.jpg', src: '/static/library/children/english/en024.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en025', name: '我的衣物', artist: '早教英语', cover: '/static/library/children/english/en025.jpg', src: '/static/library/children/english/en025.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en026', name: '我想变成一只小蜜蜂', artist: '早教英语', cover: '/static/library/children/english/en026.jpg', src: '/static/library/children/english/en026.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en027', name: '五颜六色', artist: '早教英语', cover: '/static/library/children/english/en027.jpg', src: '/static/library/children/english/en027.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en028', name: '学唱英文歌曲目01', artist: '早教英语', cover: '/static/library/children/english/en028.jpg', src: '/static/library/children/english/en028.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en029', name: '学唱英文歌曲目02', artist: '早教英语', cover: '/static/library/children/english/en029.jpg', src: '/static/library/children/english/en029.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en030', name: '学唱英文歌曲目03', artist: '早教英语', cover: '/static/library/children/english/en030.jpg', src: '/static/library/children/english/en030.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en031', name: '学唱英文歌曲目04', artist: '早教英语', cover: '/static/library/children/english/en031.jpg', src: '/static/library/children/english/en031.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en032', name: '学唱英文歌曲目05', artist: '早教英语', cover: '/static/library/children/english/en032.jpg', src: '/static/library/children/english/en032.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en033', name: '学唱英文歌曲目06', artist: '早教英语', cover: '/static/library/children/english/en033.jpg', src: '/static/library/children/english/en033.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en034', name: '学唱英文歌曲目07', artist: '早教英语', cover: '/static/library/children/english/en034.jpg', src: '/static/library/children/english/en034.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en035', name: '学唱英文歌曲目08', artist: '早教英语', cover: '/static/library/children/english/en035.jpg', src: '/static/library/children/english/en035.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en036', name: '学唱英文歌曲目09', artist: '早教英语', cover: '/static/library/children/english/en036.jpg', src: '/static/library/children/english/en036.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en037', name: '学唱英文歌曲目10', artist: '早教英语', cover: '/static/library/children/english/en037.jpg', src: '/static/library/children/english/en037.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en038', name: '学唱英文歌曲目11', artist: '早教英语', cover: '/static/library/children/english/en038.jpg', src: '/static/library/children/english/en038.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en039', name: '学唱英文歌曲目12', artist: '早教英语', cover: '/static/library/children/english/en039.jpg', src: '/static/library/children/english/en039.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en040', name: '学唱英文歌曲目13', artist: '早教英语', cover: '/static/library/children/english/en040.jpg', src: '/static/library/children/english/en040.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en041', name: '学唱英文歌曲目14', artist: '早教英语', cover: '/static/library/children/english/en041.jpg', src: '/static/library/children/english/en041.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en042', name: '学唱英文歌曲目15', artist: '早教英语', cover: '/static/library/children/english/en042.jpg', src: '/static/library/children/english/en042.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en043', name: '学唱英文歌曲目16', artist: '早教英语', cover: '/static/library/children/english/en043.jpg', src: '/static/library/children/english/en043.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en044', name: '学唱英文歌曲目17', artist: '早教英语', cover: '/static/library/children/english/en044.jpg', src: '/static/library/children/english/en044.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en045', name: '学唱英文歌曲目18', artist: '早教英语', cover: '/static/library/children/english/en045.jpg', src: '/static/library/children/english/en045.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en046', name: '学唱英文歌曲目19', artist: '早教英语', cover: '/static/library/children/english/en046.jpg', src: '/static/library/children/english/en046.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en047', name: '学唱英文歌曲目20', artist: '早教英语', cover: '/static/library/children/english/en047.jpg', src: '/static/library/children/english/en047.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en048', name: '学习反义词', artist: '早教英语', cover: '/static/library/children/english/en048.jpg', src: '/static/library/children/english/en048.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en049', name: '学习数字', artist: '早教英语', cover: '/static/library/children/english/en049.jpg', src: '/static/library/children/english/en049.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en050', name: '学习月份', artist: '早教英语', cover: '/static/library/children/english/en050.jpg', src: '/static/library/children/english/en050.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en051', name: '在动物园', artist: '早教英语', cover: '/static/library/children/english/en051.jpg', src: '/static/library/children/english/en051.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en052', name: 'a good friend', artist: '谢小禾', cover: '/static/library/children/english/en052.jpg', src: '/static/library/children/english/en052.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en053', name: 'A is for alligator', artist: '谢小禾', cover: '/static/library/children/english/en053.jpg', src: '/static/library/children/english/en053.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en054', name: 'a sailor went to sea', artist: '谢小禾', cover: '/static/library/children/english/en054.jpg', src: '/static/library/children/english/en054.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en055', name: 'An elephant in the sky(一只大象在天空)', artist: '谢小禾', cover: '/static/library/children/english/en055.jpg', src: '/static/library/children/english/en055.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en056', name: 'Build a Snowman(我们一起堆雪人)', artist: '儿童歌曲', cover: '/static/library/children/english/en056.jpg', src: '/static/library/children/english/en056.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en057', name: 'Christmas Tree(圣诞树)', artist: '谢小禾', cover: '/static/library/children/english/en057.jpg', src: '/static/library/children/english/en057.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en058', name: 'Color Words(颜色词)', artist: '谢小禾', cover: '/static/library/children/english/en058.jpg', src: '/static/library/children/english/en058.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en059', name: 'Five Little Skunks', artist: '谢小禾', cover: '/static/library/children/english/en059.jpg', src: '/static/library/children/english/en059.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en060', name: 'Five Trick-or-Treaters', artist: '谢小禾', cover: '/static/library/children/english/en060.jpg', src: '/static/library/children/english/en060.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en061', name: 'Happy Santa Claus(快乐的圣诞老人)', artist: '谢小禾', cover: '/static/library/children/english/en061.jpg', src: '/static/library/children/english/en061.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en062', name: 'I can wiggle(我能扭动)', artist: '谢小禾', cover: '/static/library/children/english/en062.jpg', src: '/static/library/children/english/en062.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en063', name: 'I Have A Wiggly，Jiggly Tooth(我有一颗摇摇晃晃的牙)', artist: '谢小禾', cover: '/static/library/children/english/en063.jpg', src: '/static/library/children/english/en063.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en064', name: 'I love christmas(我爱圣诞)', artist: '谢小禾', cover: '/static/library/children/english/en064.jpg', src: '/static/library/children/english/en064.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en065', name: 'I love the mountains(我爱大山)', artist: '谢小禾', cover: '/static/library/children/english/en065.jpg', src: '/static/library/children/english/en065.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en066', name: 'London Bridge Is Falling Down(伦敦桥)', artist: '谢小禾', cover: '/static/library/children/english/en066.jpg', src: '/static/library/children/english/en066.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en067', name: 'Michael Finnigan(迈克尔菲尼根)', artist: '谢小禾', cover: '/static/library/children/english/en067.jpg', src: '/static/library/children/english/en067.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en068', name: 'Oh Where has my little dog gone(我的小狗去哪了)', artist: '谢小禾', cover: '/static/library/children/english/en068.jpg', src: '/static/library/children/english/en068.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en069', name: 'Pat a Cake(做蛋糕)', artist: '谢小禾', cover: '/static/library/children/english/en069.jpg', src: '/static/library/children/english/en069.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en070', name: 'Santa Claus came to my house(圣诞老人来我家)', artist: '谢小禾', cover: '/static/library/children/english/en070.jpg', src: '/static/library/children/english/en070.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en071', name: 'Sea Otter Won\'t You Play With Me(海獭，你能跟我一起玩吗)', artist: '谢小禾', cover: '/static/library/children/english/en071.jpg', src: '/static/library/children/english/en071.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en072', name: 'Sing a song(唱唱唱首歌)', artist: '谢小禾', cover: '/static/library/children/english/en072.jpg', src: '/static/library/children/english/en072.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en073', name: 'Sing Your Way Home(一路唱歌回家去)', artist: '谢小禾', cover: '/static/library/children/english/en073.jpg', src: '/static/library/children/english/en073.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en074', name: 'Ten in the Bed', artist: '谢小禾', cover: '/static/library/children/english/en074.jpg', src: '/static/library/children/english/en074.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en075', name: 'The Big Rock Candy Mountains(巨石糖果山)', artist: '谢小禾', cover: '/static/library/children/english/en075.jpg', src: '/static/library/children/english/en075.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en076', name: 'the muffin man(松饼师)', artist: '谢小禾', cover: '/static/library/children/english/en076.jpg', src: '/static/library/children/english/en076.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en077', name: 'The Twelve Days Of Christmas', artist: '谢小禾', cover: '/static/library/children/english/en077.jpg', src: '/static/library/children/english/en077.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en078', name: 'To Market(去市场)', artist: '谢小禾', cover: '/static/library/children/english/en078.jpg', src: '/static/library/children/english/en078.mp3', category: 'children', subCategory: 'children-english' },
  { id: 'en079', name: 'Up On The Housetop', artist: '谢小禾', cover: '/static/library/children/english/en079.jpg', src: '/static/library/children/english/en079.mp3', category: 'children', subCategory: 'children-english' },

  // ===== 古诗 poetry =====
  { id: 'gs001', name: '咏鹅', artist: '骆宾王', album: '唐诗', cover: '/static/covers/gs001.jpg', src: '/static/audio/gs001.mp3', category: 'poetry', subCategory: 'poetry-tang',
    lyric: ['[00:00.00]咏鹅 · 骆宾王', '[00:03.00]鹅,鹅,鹅,', '[00:06.00]曲项向天歌。', '[00:09.00]白毛浮绿水,', '[00:12.00]红掌拨清波。'].join('\n') },
  { id: 'gs002', name: '静夜思', artist: '李白', album: '唐诗', cover: '/static/covers/gs002.jpg', src: '/static/audio/gs002.mp3', category: 'poetry', subCategory: 'poetry-tang',
    lyric: ['[00:00.00]静夜思 · 李白', '[00:04.00]床前明月光,', '[00:08.00]疑是地上霜。', '[00:12.00]举头望明月,', '[00:16.00]低头思故乡。'].join('\n') },
  { id: 'gs003', name: '春晓', artist: '孟浩然', album: '唐诗', cover: '/static/covers/gs003.jpg', src: '/static/audio/gs003.mp3', category: 'poetry', subCategory: 'poetry-tang',
    lyric: ['[00:00.00]春晓 · 孟浩然', '[00:04.00]春眠不觉晓,', '[00:08.00]处处闻啼鸟。', '[00:12.00]夜来风雨声,', '[00:16.00]花落知多少。'].join('\n') },
  { id: 'gs004', name: '水调歌头', artist: '苏轼', album: '宋词', cover: '/static/covers/gs004.jpg', src: '/static/audio/gs004.mp3', category: 'poetry', subCategory: 'poetry-song',
    lyric: ['[00:00.00]水调歌头 · 苏轼', '[00:05.00]明月几时有,把酒问青天。(示例歌词)'].join('\n') },
  { id: 'gs005', name: '如梦令', artist: '李清照', album: '宋词', cover: '/static/covers/gs005.jpg', src: '/static/audio/gs005.mp3', category: 'poetry', subCategory: 'poetry-song',
    lyric: ['[00:00.00]如梦令 · 李清照', '[00:05.00]常记溪亭日暮,沉醉不知归路。(示例歌词)'].join('\n') },
  { id: 'gs006', name: '望庐山瀑布', artist: '李白', album: '七言绝句', cover: '/static/covers/gs006.jpg', src: '/static/audio/gs006.mp3', category: 'poetry', subCategory: 'poetry-seven',
    lyric: ['[00:00.00]望庐山瀑布 · 李白', '[00:05.00]日照香炉生紫烟,遥看瀑布挂前川。(示例歌词)'].join('\n') },
  { id: 'gs007', name: '枫桥夜泊', artist: '张继', album: '七言绝句', cover: '/static/covers/gs007.jpg', src: '/static/audio/gs007.mp3', category: 'poetry', subCategory: 'poetry-seven',
    lyric: ['[00:00.00]枫桥夜泊 · 张继', '[00:05.00]月落乌啼霜满天,江枫渔火对愁眠。(示例歌词)'].join('\n') },

  // ===== 国学 classics =====
  { id: 'szj001', name: '三字经(人之初)', artist: '王应麟', album: '国学经典', cover: '/static/covers/szj001.jpg', src: '/static/audio/szj001.mp3', category: 'classics', subCategory: 'classics-sanzijing',
    lyric: ['[00:00.00]三字经 · 王应麟', '[00:04.00]人之初,性本善。', '[00:08.00]性相近,习相远。', '[00:12.00]苟不教,性乃迁。', '[00:16.00]教之道,贵以专。'].join('\n') },
  { id: 'dzg001', name: '弟子规(总叙)', artist: '李毓秀', album: '国学经典', cover: '/static/covers/dzg001.jpg', src: '/static/audio/dzg001.mp3', category: 'classics', subCategory: 'classics-dizigui',
    lyric: ['[00:00.00]弟子规 · 李毓秀', '[00:04.00]弟子规,圣人训。', '[00:08.00]首孝悌,次谨信。(示例歌词)'].join('\n') },
  { id: 'bjx001', name: '百家姓', artist: '佚名', album: '国学经典', cover: '/static/covers/bjx001.jpg', src: '/static/audio/bjx001.mp3', category: 'classics', subCategory: 'classics-baijia',
    lyric: ['[00:00.00]百家姓', '[00:04.00]赵钱孙李,周吴郑王。(示例歌词)'].join('\n') },
  { id: 'qzw001', name: '千字文', artist: '周兴嗣', album: '国学经典', cover: '/static/covers/qzw001.jpg', src: '/static/audio/qzw001.mp3', category: 'classics', subCategory: 'classics-qianzi',
    lyric: ['[00:00.00]千字文 · 周兴嗣', '[00:04.00]天地玄黄,宇宙洪荒。(示例歌词)'].join('\n') },

  // ===== 故事 story =====
  { id: 'story001', name: '龟兔赛跑', artist: '伊索寓言', album: '寓言故事', cover: '/static/covers/story001.jpg', src: '/static/audio/story001.mp3', category: 'story', subCategory: 'story-fable' },
  { id: 'story002', name: '狼来了', artist: '伊索寓言', album: '寓言故事', cover: '/static/covers/story002.jpg', src: '/static/audio/story002.mp3', category: 'story', subCategory: 'story-fable' },
  { id: 'story003', name: '白雪公主', artist: '格林童话', album: '童话故事', cover: '/static/covers/story003.jpg', src: '/static/audio/story003.mp3', category: 'story', subCategory: 'story-fairy' },
  { id: 'story004', name: '灰姑娘', artist: '格林童话', album: '童话故事', cover: '/static/covers/story004.jpg', src: '/static/audio/story004.mp3', category: 'story', subCategory: 'story-fairy' },
  { id: 'story005', name: '守株待兔', artist: '成语故事', album: '成语故事', cover: '/static/covers/story005.jpg', src: '/static/audio/story005.mp3', category: 'story', subCategory: 'story-idiom' },
  { id: 'story006', name: '亡羊补牢', artist: '成语故事', album: '成语故事', cover: '/static/covers/story006.jpg', src: '/static/audio/story006.mp3', category: 'story', subCategory: 'story-idiom' },
  { id: 'story007', name: '盘古开天', artist: '神话故事', album: '神话故事', cover: '/static/covers/story007.jpg', src: '/static/audio/story007.mp3', category: 'story', subCategory: 'story-myth' },
  { id: 'story008', name: '嫦娥奔月', artist: '神话故事', album: '神话故事', cover: '/static/covers/story008.jpg', src: '/static/audio/story008.mp3', category: 'story', subCategory: 'story-myth' },
];

/** 按 id 建立索引,便于 O(1) 查找 */
export const songMap: Record<string, Song> = songs.reduce(
  (map, song) => {
    map[song.id] = song;
    return map;
  },
  {} as Record<string, Song>,
);
