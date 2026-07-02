/**
 * 通用格式化工具。
 */

/**
 * 把秒数格式化为 mm:ss 形式。
 * @param seconds 秒数(可为小数)
 * @returns 如 "03:05";非有效值返回 "00:00"
 */
export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '00:00';
  const total = Math.floor(seconds);
  const minutes = Math.floor(total / 60);
  const secs = total % 60;
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  return `${pad(minutes)}:${pad(secs)}`;
}
