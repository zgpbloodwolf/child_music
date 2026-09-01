/**
 * 从音频目录导入剩余的唐诗三百首
 *
 * 配置通过环境变量注入（避免把真实 token / 本机路径硬编码入库）:
 *   IMPORT_BASE_URL     后端 API 地址
 *   IMPORT_ADMIN_TOKEN  管理接口鉴权 token
 *   IMPORT_GUSHI_DIR    古诗音频目录
 *   IMPORT_POETRY_JSON  诗.json 路径
 *   IMPORT_MANIFEST     manifest.jsonl 路径
 */

const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const fetch = require('node-fetch');

const CONFIG = {
  baseUrl: process.env.IMPORT_BASE_URL || 'http://127.0.0.1:8823/childmusic',
  adminToken: process.env.IMPORT_ADMIN_TOKEN || '',
  gushiDir: process.env.IMPORT_GUSHI_DIR || '',
  poetryJson: process.env.IMPORT_POETRY_JSON || '',
  manifestPath: process.env.IMPORT_MANIFEST || '',
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
  console.log('=== 从音频目录导入剩余唐诗三百首 ===\n');

  // 校验必填配置
  const missing = [];
  if (!CONFIG.adminToken) missing.push('IMPORT_ADMIN_TOKEN');
  if (!CONFIG.gushiDir) missing.push('IMPORT_GUSHI_DIR');
  if (!CONFIG.poetryJson) missing.push('IMPORT_POETRY_JSON');
  if (!CONFIG.manifestPath) missing.push('IMPORT_MANIFEST');
  if (missing.length > 0) {
    console.error(`缺少环境变量: ${missing.join(', ')}`);
    process.exit(1);
  }

  // 1. 获取现有 tang300 歌曲
  console.log('获取现有歌曲...');
  const existingSongs = await request(`/api/songs?category=${CONFIG.categoryId}&sub=${CONFIG.subCategoryId}`);
  const existingIds = new Set(existingSongs.map(s => s.id));
  console.log(`现有歌曲: ${existingSongs.length} 首\n`);

  // 2. 读取诗.json获取唐诗三百首列表
  const poems = JSON.parse(fs.readFileSync(CONFIG.poetryJson, 'utf8'));
  const ts300 = poems.filter(p => p.type && p.type.includes('唐诗三百首'));

  // 3. 读取manifest.jsonl
  const manifest = fs.readFileSync(CONFIG.manifestPath, 'utf8');
  const manifestMap = new Map();
  for (const line of manifest.trim().split('\n')) {
    try {
      const item = JSON.parse(line);
      manifestMap.set(item.id, item);
    } catch {}
  }

  // 4. 读取G盘文件列表
  const allGushiFiles = fs.readdirSync(CONFIG.gushiDir);

  // 5. 找出需要导入的诗词
  const toImport = [];

  for (const poem of ts300) {
    // 跳过已存在的
    const expectedId = `tang300_${poem.id}`;
    if (existingIds.has(expectedId)) continue;

    // 在manifest中查找
    for (const [id, item] of manifestMap) {
      if (item.title === poem.title && item.author === poem.author &&
          item.type && item.type.includes('唐诗三百首')) {
        // 在G盘查找文件
        const gushiFile = allGushiFiles.find(f => f.endsWith('.mp3') && f.includes(id));
        if (gushiFile) {
          toImport.push({
            id: expectedId,
            name: poem.title,
            author: poem.author,
            audioPath: path.join(CONFIG.gushiDir, gushiFile),
            lrcPath: path.join(CONFIG.gushiDir, gushiFile.replace('.mp3', '.lrc')),
          });
        }
        break;
      }
    }
  }

  console.log(`待导入: ${toImport.length} 首\n`);

  // 6. 导入
  let success = 0;
  let failed = 0;

  for (let i = 0; i < toImport.length; i++) {
    const item = toImport[i];
    const progress = `[${i + 1}/${toImport.length}]`;
    process.stdout.write(`${progress} ${item.name} - ${item.author}...`);

    if (!fs.existsSync(item.audioPath)) {
      console.log(' ✗ 音频文件不存在');
      failed++;
      continue;
    }

    const form = new FormData();
    form.append('id', item.id);
    form.append('name', item.name);
    form.append('artist', item.author);
    form.append('category_id', CONFIG.categoryId);
    form.append('sub_category_id', CONFIG.subCategoryId);
    form.append('audio', fs.createReadStream(item.audioPath));

    if (fs.existsSync(item.lrcPath)) {
      form.append('lyric', fs.readFileSync(item.lrcPath, 'utf8'));
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

    if ((i + 1) % 10 === 0) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  console.log('\n=== 导入完成 ===');
  console.log(`成功: ${success} 首`);
  console.log(`失败: ${failed} 首`);
  console.log(`总计: ${existingSongs.length + success} 首`);
}

main().catch(e => {
  console.error('导入失败:', e);
  process.exit(1);
});
