/**
 * 跨端加载 static 下的 JSON 资源(仅 App + H5,小程序不在目标端)。
 * - H5:用 fetch 读网站静态资源
 * - App:用 plus.io 读取打包在 _www 下的本地文件
 *
 * 注:App 端 plus.io 读取本地 static 文件的行为待真机验证(本环境仅做类型检查)。
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
          resolveLocalFileURL: (
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
            readAsText: (f: unknown) => void;
          };
        };
      };
    };
    const io = g.plus?.io;
    if (!io) {
      reject(new Error('App 端 plus.io 不可用'));
      return;
    }
    io.resolveLocalFileURL(
      url,
      (entry) => {
        entry.file(
          (file) => {
            const reader = new io.FileReader();
            reader.onloadend = () => {
              const text = reader.result;
              if (typeof text !== 'string') {
                reject(new Error('读取结果非文本'));
                return;
              }
              try {
                resolve(JSON.parse(text) as T);
              } catch (err) {
                reject(err);
              }
            };
            reader.onerror = () => reject(new Error(`读取文件失败: ${url}`));
            reader.readAsText(file);
          },
          (err) => reject(err),
        );
      },
      (err) => reject(err),
    );
  });
  // #endif
}
