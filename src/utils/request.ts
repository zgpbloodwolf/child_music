/**
 * 统一请求封装:基于 uni.request,收敛 baseURL、超时与错误处理。
 *
 * 约定(见 CLAUDE.md 第 5 节):所有请求走本封装,禁止裸 uni.request。
 * 成功返回解析后的 JSON 数据(泛型 T);非 2xx / 网络失败抛 RequestError(含中文提示)。
 */
import { API_BASE_URL } from '@/config';

/** 请求选项 */
export interface RequestOptions {
  /** 相对 API_BASE_URL 的路径(如 /api/songs),或完整 http(s) URL */
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  /** 请求体(GET 时通常不用,通过 params 传查询参数) */
  data?: Record<string, unknown> | string;
  /** 查询参数,自动序列化为 querystring,自动过滤空值 */
  params?: Record<string, string | number | undefined | null>;
  /** 自定义请求头 */
  header?: Record<string, string>;
  /** 超时(ms),默认 15000 */
  timeout?: number;
}

/** 请求错误:携带状态码(0 表示网络层失败)与可读信息 */
export class RequestError extends Error {
  constructor(
    public readonly statusCode: number,
    message: string,
  ) {
    super(message);
    this.name = 'RequestError';
  }
}

/** 组装完整 URL:拼接 baseURL + 查询参数(querystring) */
function buildUrl(url: string, params?: RequestOptions['params']): string {
  const full = /^https?:\/\//.test(url) ? url : `${API_BASE_URL}${url}`;
  if (!params) return full;
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  if (!qs) return full;
  return full.includes('?') ? `${full}&${qs}` : `${full}?${qs}`;
}

/** 从后端错误响应里提取可读信息(FastAPI 错误体形如 { detail: ... }) */
function extractDetail(data: unknown): unknown {
  if (data && typeof data === 'object' && 'detail' in data) {
    return (data as { detail: unknown }).detail;
  }
  return data;
}

/** 发起请求,返回解析后的数据 */
export function request<T = unknown>(opts: RequestOptions): Promise<T> {
  const method = opts.method ?? 'GET';
  const url = buildUrl(opts.url, opts.params);
  return new Promise<T>((resolve, reject) => {
    uni.request({
      url,
      method,
      data: opts.data,
      timeout: opts.timeout ?? 15000,
      header: { 'Content-Type': 'application/json', ...opts.header },
      success: (res) => {
        const status = res.statusCode ?? 0;
        if (status >= 200 && status < 300) {
          resolve(res.data as T);
          return;
        }
        console.error(`[request] ${method} ${url} 失败:`, status, extractDetail(res.data));
        reject(new RequestError(status, `请求失败(${status})`));
      },
      fail: (err) => {
        console.error(`[request] ${method} ${url} 网络错误:`, err);
        reject(new RequestError(0, '网络请求失败,请检查网络或服务是否可用'));
      },
    });
  });
}
