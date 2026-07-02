/**
 * 歌曲相关类型定义。
 */

/**
 * 歌曲列表展示用的轻量元数据(不含音频地址 src、歌词 lyric)。
 * 首页 / 搜索 / 收藏 / 历史等列表场景只需这些字段;真正播放时再取完整 Song。
 * 与未来「按需加载」架构对应:列表只载入轻量元数据,降低内存与首屏开销。
 */
export interface SongMeta {
  /** 唯一标识 */
  id: string;
  /** 名称(儿歌名/古诗名/故事名等) */
  name: string;
  /** 作者/来源(如「李白」「经典儿歌」「格林童话」) */
  artist: string;
  /** 专辑/合集(可选,如「唐诗」) */
  album?: string;
  /** 封面图路径,如 /static/covers/gs001.jpg(为空时组件用色块占位兜底) */
  cover: string;
  /** 时长,单位秒(可选;实际播放时长以播放器回调为准) */
  duration?: number;
  /** 所属大类 id:children / poetry / classics / story */
  category: string;
  /** 所属子分类 id(主归属),如 poetry-tang */
  subCategory?: string;
}

/**
 * 完整歌曲信息:在 SongMeta 基础上增加播放所需的音频地址与歌词。
 * 继承 SongMeta,因此任何接受 SongMeta 的地方都能直接传入 Song。
 */
export interface Song extends SongMeta {
  /** 音频文件路径,如 /static/audio/gs001.mp3 */
  src: string;
  /** 歌词文本(lrc 格式字符串,内嵌以便跨端一致加载;可选) */
  lyric?: string;
}

/** 播放模式 */
export enum PlayMode {
  /** 顺序播放:播完当前列表自动下一首,末尾停止 */
  SEQUENCE = 'sequence',
  /** 单曲循环 */
  LOOP_ONE = 'loop_one',
  /** 随机播放 */
  RANDOM = 'random',
}
