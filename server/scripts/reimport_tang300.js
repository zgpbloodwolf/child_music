/**
 * 唐诗三百首重新导入脚本
 * 1. 删除旧的 tang300 歌曲数据
 * 2. 从诗音频目录读取新文件
 * 3. 重新导入（使用 manifest.jsonl 的 id）
 *
 * 配置通过环境变量注入（避免把真实 token / 本机路径硬编码入库）:
 *   IMPORT_BASE_URL     后端 API 地址
 *   IMPORT_ADMIN_TOKEN  管理接口鉴权 token
 *   IMPORT_MANIFEST     manifest.jsonl 路径
 *   IMPORT_POETRY_DIR   诗音频目录
 *   IMPORT_POETRY_JSON  诗.json 路径
 */

const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const fetch = require('node-fetch');

const CONFIG = {
  baseUrl: process.env.IMPORT_BASE_URL || 'http://127.0.0.1:8823/childmusic',
  adminToken: process.env.IMPORT_ADMIN_TOKEN || '',
  manifestPath: process.env.IMPORT_MANIFEST || '',
  poetryDir: process.env.IMPORT_POETRY_DIR || '',
  poetryJson: process.env.IMPORT_POETRY_JSON || '',
  categoryId: 'poetry',
  subCategoryId: 'tang300',
};

async function request(endpoint, options = {}) {
  const url = `${CONFIG.baseUrl}${endpoint}`;
  const headers = { 'Authorization': `Bearer ${CONFIG.adminToken}`, ...options.headers };
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${endpoint}: ${response.status} ${text}`);
  }
  return response.json();
}

async function main() {
  console.log('=== 唐诗三百首重新导入 ===\n');

  // 校验必填配置
  const missing = [];
  if (!CONFIG.adminToken) missing.push('IMPORT_ADMIN_TOKEN');
  if (!CONFIG.manifestPath) missing.push('IMPORT_MANIFEST');
  if (!CONFIG.poetryDir) missing.push('IMPORT_POETRY_DIR');
  if (!CONFIG.poetryJson) missing.push('IMPORT_POETRY_JSON');
  if (missing.length > 0) {
    console.error(`缺少环境变量: ${missing.join(', ')}`);
    process.exit(1);
  }

  // 1. 获取现有 tang300 歌曲列表
  console.log('获取现有歌曲列表...');
  const existingSongs = await request(`/api/songs?category=${CONFIG.categoryId}&sub=${CONFIG.subCategoryId}`);
  console.log(`现有歌曲: ${existingSongs.length} 首`);

  // 2. 删除旧数据
  console.log('\n删除旧数据...');
  let deleted = 0;
  for (const song of existingSongs) {
    try {
      await request(`/api/admin/songs/${song.id}`, { method: 'DELETE' });
      deleted++;
      process.stdout.write(`\r已删除: ${deleted}/${existingSongs.length}`);
    } catch (e) {
      console.log(`\n删除失败 ${song.id}: ${e.message}`);
    }
  }
  console.log(`\n删除完成: ${deleted} 首\n`);

  // 3. 读取 manifest.jsonl 筛选唐诗三百首
  console.log('读取 manifest.jsonl...');
  const manifest = fs.readFileSync(CONFIG.manifestPath, 'utf8');
  const lines = manifest.trim().split('\n');

  const manifestMap = new Map();
  for (const line of lines) {
    try {
      const item = JSON.parse(line);
      manifestMap.set(item.id, item);
    } catch {}
  }

  // 4. 读取诗目录文件列表
  const allFiles = fs.readdirSync(CONFIG.poetryDir);
  const mp3Files = allFiles.filter(f => f.endsWith('.mp3'));

  // 5. 从诗.json获取唐诗三百首列表
  const poems = JSON.parse(fs.readFileSync(CONFIG.poetryJson, 'utf8'));
  const ts300 = poems.filter(p => p.type && p.type.includes('唐诗三百首'));

  // 6. 匹配文件
  console.log('匹配文件...');
  const toImport = [];
  const missing = [];

  for (const poem of ts300) {
    const prefix = `${poem.title}-${poem.author}-`;
    const matchFile = mp3Files.find(f => f.startsWith(prefix));

    if (matchFile) {
      // 从文件名提取 id
      const id = matchFile.replace('.mp3', '').split('-').pop();
      const manifestItem = manifestMap.get(id);

      if (manifestItem) {
        toImport.push({
          id: `tang300_${id}`,
          name: poem.title,
          author: poem.author,
          audioPath: path.join(CONFIG.poetryDir, matchFile),
          lrcPath: path.join(CONFIG.poetryDir, matchFile.replace('.mp3', '.lrc')),
          manifestItem,
        });
      }
    } else {
      missing.push(`${poem.title} - ${poem.author}`);
    }
  }

  console.log(`待导入: ${toImport.length} 首`);
  console.log(`缺少文件: ${missing.length} 首\n`);

  if (missing.length > 0) {
    console.log('缺少文件的诗词:');
    missing.slice(0, 20).forEach(m => console.log(`  - ${m}`));
    if (missing.length > 20) console.log(`  ... 还有 ${missing.length - 20} 首`);
    console.log('');
  }

  // 7. 逐首导入
  console.log('开始导入...');
  let success = 0;
  let failed = 0;

  for (let i = 0; i < toImport.length; i++) {
    const item = toImport[i];
    const progress = `[${i + 1}/${toImport.length}]`;
    process.stdout.write(`${progress} ${item.name} - ${item.author}...`);

    const form = new FormData();
    form.append('id', item.id);
    form.append('name', item.name);
    form.append('artist', item.author);
    form.append('category_id', CONFIG.categoryId);
    form.append('sub_category_id', CONFIG.subCategoryId);
    form.append('audio', fs.createReadStream(item.audioPath));

    // 读取LRC歌词
    if (fs.existsSync(item.lrcPath)) {
      const lyric = fs.readFileSync(item.lrcPath, 'utf8');
      form.append('lyric', lyric);
    }

    try {
      await request('/api/admin/songs', {
        method: 'POST',
        body: form,
        headers: form.getHeaders(),
      });
      console.log(' ✓');
      success++;
    } catch (e) {
      console.log(` ✗ ${e.message.substring(0, 60)}`);
      failed++;
    }

    // 每10首休息一下
    if ((i + 1) % 10 === 0) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  console.log('\n=== 导入完成 ===');
  console.log(`成功: ${success} 首`);
  console.log(`失败: ${failed} 首`);
  console.log(`缺少音频: ${missing.length} 首`);
}

main().catch(e => {
  console.error('导入失败:', e);
  process.exit(1);
});
