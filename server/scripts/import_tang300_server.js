/**
 * 唐诗三百首导入脚本（服务器版本）
 * 从本地数据导入到远程服务器
 *
 * 配置通过环境变量注入（避免把真实地址/token 硬编码入库）：
 *   IMPORT_BASE_URL    后端 API 地址，如 http://<服务器地址>:8823/cmusic
 *   IMPORT_ADMIN_TOKEN 管理接口鉴权 token（与服务端 .env 的 ADMIN_TOKEN 一致）
 *   IMPORT_MANIFEST    manifest.jsonl 路径
 *   IMPORT_GUSHI_DIR   古诗音频目录
 *   IMPORT_POETRY_DIR  诗音频目录
 */

const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const fetch = require('node-fetch');

const CONFIG = {
  baseUrl: process.env.IMPORT_BASE_URL || 'http://127.0.0.1:8823/cmusic',
  adminToken: process.env.IMPORT_ADMIN_TOKEN || '',

  manifestPath: process.env.IMPORT_MANIFEST || '',
  gushiDir: process.env.IMPORT_GUSHI_DIR || '',
  poetryDir: process.env.IMPORT_POETRY_DIR || '',

  // 分类配置
  categoryId: 'poetry',
  categoryName: '古诗词',
  categoryIcon: '📜',
  categoryDesc: '经典古诗词朗诵',

  subCategoryId: 'tang300',
  subCategoryName: '唐诗三百首',
  subCategoryIcon: '🎵',
  subCategoryDesc: '唐诗三百首选集',
};

async function request(endpoint, options = {}) {
  const url = `${CONFIG.baseUrl}${endpoint}`;
  const headers = {
    'Authorization': `Bearer ${CONFIG.adminToken}`,
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${endpoint}: ${response.status} ${text}`);
  }

  return response.json();
}

async function main() {
  console.log('=== 唐诗三百首导入工具（服务器版）===\n');

  // 校验必填配置,避免空值导致后续请求失败
  const missing = [];
  if (!CONFIG.adminToken) missing.push('IMPORT_ADMIN_TOKEN');
  if (!CONFIG.manifestPath) missing.push('IMPORT_MANIFEST');
  if (!CONFIG.gushiDir) missing.push('IMPORT_GUSHI_DIR');
  if (!CONFIG.poetryDir) missing.push('IMPORT_POETRY_DIR');
  if (missing.length > 0) {
    console.error(`缺少环境变量: ${missing.join(', ')}`);
    console.error('示例:\n  set IMPORT_BASE_URL=http://127.0.0.1:8823/cmusic\n  set IMPORT_ADMIN_TOKEN=<token>\n  set IMPORT_MANIFEST=<manifest.jsonl 路径>');
    process.exit(1);
  }

  try {
    // 1. 创建分类
    console.log('创建大类:', CONFIG.categoryName);
    try {
      await request('/api/admin/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: CONFIG.categoryId,
          name: CONFIG.categoryName,
          icon: CONFIG.categoryIcon,
          desc: CONFIG.categoryDesc,
        }),
      });
      console.log('✓ 大类创建成功');
    } catch (e) {
      if (e.message.includes('已存在')) {
        console.log('✓ 大类已存在，跳过');
      } else throw e;
    }

    console.log('创建子类:', CONFIG.subCategoryName);
    try {
      await request('/api/admin/subs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: CONFIG.subCategoryId,
          category_id: CONFIG.categoryId,
          name: CONFIG.subCategoryName,
          icon: CONFIG.subCategoryIcon,
          desc: CONFIG.subCategoryDesc,
        }),
      });
      console.log('✓ 子类创建成功');
    } catch (e) {
      if (e.message.includes('已存在')) {
        console.log('✓ 子类已存在，跳过');
      } else throw e;
    }

    // 2. 读取 manifest.jsonl 中的唐诗三百首
    console.log('\n读取 manifest.jsonl...');
    const manifest = fs.readFileSync(CONFIG.manifestPath, 'utf8');
    const manifestTs300 = [];
    for (const line of manifest.trim().split('\n')) {
      try {
        const item = JSON.parse(line);
        if (item.type && item.type.includes('唐诗三百首')) {
          manifestTs300.push(item);
        }
      } catch {}
    }
    console.log(`✓ 找到 ${manifestTs300.length} 首唐诗三百首`);

    // 3. 获取服务器上已有的歌曲
    console.log('\n检查服务器现有数据...');
    let existingIds = new Set();
    try {
      const existing = await request(`/api/songs?category=${CONFIG.categoryId}&sub=${CONFIG.subCategoryId}`);
      existingIds = new Set(existing.map(s => s.id));
      console.log(`✓ 服务器已有 ${existing.length} 首`);
    } catch (e) {
      console.log('查询失败，将全部导入');
    }

    // 4. 导入歌曲
    console.log('\n开始导入...');
    const gushiFiles = fs.readdirSync(CONFIG.gushiDir);
    const poetryFiles = fs.readdirSync(CONFIG.poetryDir);

    let success = 0;
    let skipped = 0;
    let failed = 0;

    for (let i = 0; i < manifestTs300.length; i++) {
      const item = manifestTs300[i];
      const songId = `tang300_${item.id}`;
      const progress = `[${i + 1}/${manifestTs300.length}]`;

      // 跳过已存在的
      if (existingIds.has(songId)) {
        skipped++;
        continue;
      }

      // 查找音频文件（先找 G 盘，再找诗目录）
      let audioPath = null;
      const gushiFile = gushiFiles.find(f => f.endsWith('.mp3') && f.includes(item.id));
      if (gushiFile) {
        audioPath = path.join(CONFIG.gushiDir, gushiFile);
      } else {
        const poetryFile = poetryFiles.find(f => f.endsWith('.mp3') && f.includes(item.id));
        if (poetryFile) {
          audioPath = path.join(CONFIG.poetryDir, poetryFile);
        }
      }

      if (!audioPath || !fs.existsSync(audioPath)) {
        process.stdout.write(`${progress} ${item.title} - ${item.author}... ✗ 音频不存在\n`);
        failed++;
        continue;
      }

      process.stdout.write(`${progress} ${item.title} - ${item.author}...`);

      const form = new FormData();
      form.append('id', songId);
      form.append('name', item.title);
      form.append('artist', item.author);
      form.append('category_id', CONFIG.categoryId);
      form.append('sub_category_id', CONFIG.subCategoryId);
      form.append('audio', fs.createReadStream(audioPath));

      // 查找 LRC 文件
      const lrcFile = audioPath.replace('.mp3', '.lrc');
      if (fs.existsSync(lrcFile)) {
        form.append('lyric', fs.readFileSync(lrcFile, 'utf8'));
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
        console.log(` ✗ ${e.message.substring(0, 50)}`);
        failed++;
      }

      // 每 10 首休息一下
      if ((i + 1) % 10 === 0) {
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    }

    console.log('\n=== 导入完成 ===');
    console.log(`成功: ${success} 首`);
    console.log(`跳过: ${skipped} 首（已存在）`);
    console.log(`失败: ${failed} 首`);
    console.log(`总计: ${success + skipped} 首`);

  } catch (error) {
    console.error('\n导入失败:', error);
    process.exit(1);
  }
}

main();
