/**
 * 跨端加载 static 下的 JSON 资源(仅 App + H5,小程序不在目标端)。
 * - H5:用 fetch 读网站静态资源
 * - App:用 plus.io 读取打包在 _www 下的本地文件
 *
 * App 端关键点:打包后 static 资源位于 _www 目录(只读),传入的项目相对路径
 * (如 /static/...)必须归一化为 _www 相对路径(如 _www/static/...)才能被
 * resolveLocalFileSystemURL 解析,否则进入 fail 回调、上层 warmup 抛错导致「无数据」。
 *
 * plus 类型在此内联声明,不依赖外部 @types,保证类型检查稳定。
 */
export function loadJson<T>(url: string): Promise<T> {
  // #ifdef H5
  return fetch(url).then(async (res) => {
    if (!res.ok) throw new Error(`加载 JSON 失败: ${url} (${res.status})`);
    return (await res.json()) as T;
  });
  // #endif

  // #ifdef APP-PLUS
  return new Promise<T>((resolve, reject) => {
    const g = globalThis as unknown as {
      plus?: {
        io: {
          resolveLocalFileSystemURL: (
            url: string,
            ok: (entry: {
              file: (ok: (f: unknown) => void, fail: (e: unknown) => void) => void;
            }) => void,
            fail: (e: unknown) => void,
          ) => void;
          FileReader: new () => {
            result: string | null;
            onloadend: (() => void) | null;
            onerror: (() => void) | null;
            readAsText: (f: unknown, encoding?: string) => void;
          };
        };
      };
    };
    const io = g.plus?.io;
    if (!io) {
      reject(new Error('App 端 plus.io 不可用'));
      return;
    }
    // 项目相对路径(如 /static/...) -> _www 相对路径(如 _www/static/...),
    // 去掉前导斜杠并补 _www 前缀;打包后 static 资源只读地位于该目录下。
    const wwwUrl = `_www/${url.replace(/^\/+/, '')}`;
    /** plus 的错误对象不直观,统一转成带路径与原始信息的 Error,便于真机排查 */
    const toErr = (e: unknown) =>
      new Error(
        `加载 JSON 失败: ${wwwUrl} (${typeof e === 'object' && e ? JSON.stringify(e) : String(e)})`,
      );
    io.resolveLocalFileSystemURL(
      wwwUrl,
      (entry) => {
        entry.file(
          (file) => {
            const reader = new io.FileReader();
            reader.onloadend = () => {
              const text = reader.result;
              if (typeof text !== 'string') {
                reject(new Error(`读取结果非文本: ${wwwUrl}`));
                return;
              }
              try {
                resolve(JSON.parse(text) as T);
              } catch (err) {
                reject(err);
              }
            };
            reader.onerror = () => reject(toErr(new Error(`读取文件失败: ${wwwUrl}`)));
            reader.readAsText(file, 'utf-8');
          },
          (err) => reject(toErr(err)),
        );
      },
      (err) => reject(toErr(err)),
    );
  });
  // #endif
}
