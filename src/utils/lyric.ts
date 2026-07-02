/**
 * 歌词(lrc)解析工具。
 */

/** 单行歌词 */
export interface LyricLine {
  /** 该行开始时间,单位秒 */
  time: number;
  /** 歌词文本 */
  text: string;
}

/**
 * 解析 lrc 歌词字符串为按时间升序的歌词行数组。
 * 支持一行多个时间标签(如 [00:01.00][00:30.00] 同一句)。
 * @param lrc lrc 格式字符串
 */
export function parseLyric(lrc: string): LyricLine[] {
  if (!lrc) return [];
  const lines = lrc.split(/\r?\n/);
  const result: LyricLine[] = [];
  // 匹配 [mm:ss] 或 [mm:ss.ms] 时间标签
  const timeReg = /\[(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?\]/g;

  for (const line of lines) {
    const times: number[] = [];
    let match: RegExpExecArray | null;
    timeReg.lastIndex = 0;
    while ((match = timeReg.exec(line)) !== null) {
      const minutes = parseInt(match[1], 10);
      const seconds = parseInt(match[2], 10);
      const ms = match[3] ? parseInt(match[3].padEnd(3, '0'), 10) : 0;
      times.push(minutes * 60 + seconds + ms / 1000);
    }
    const text = line.replace(timeReg, '').trim();
    for (const t of times) {
      result.push({ time: t, text });
    }
  }

  result.sort((a, b) => a.time - b.time);
  return result;
}
