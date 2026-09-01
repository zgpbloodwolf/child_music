/**
 * 唐诗三百首导入脚本
 * 通过管理 API 导入到音乐应用后端
 *
 * 配置通过环境变量注入（避免把真实 token / 本机路径硬编码入库）:
 *   IMPORT_BASE_URL    后端 API 地址,如 http://127.0.0.1:8823/childmusic
 *   IMPORT_ADMIN_TOKEN 管理接口鉴权 token(与服务端 .env 的 ADMIN_TOKEN 一致)
 *   IMPORT_MANIFEST    manifest.jsonl 路径
 *   IMPORT_AUDIO_DIR   音频文件目录
 */

const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const fetch = require('node-fetch');

// 配置
const CONFIG = {
  // 后端API地址
  baseUrl: process.env.IMPORT_BASE_URL || 'http://127.0.0.1:8823/childmusic',
  adminToken: process.env.IMPORT_ADMIN_TOKEN || '',

  // 数据源路径
  manifestPath: process.env.IMPORT_MANIFEST || '',
  audioDir: process.env.IMPORT_AUDIO_DIR || '',

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

// 辅助函数：发送请求
async function request(endpoint, options = {}) {
  const url = `${CONFIG.baseUrl}${endpoint}`;
  const headers = {
    'Authorization': `Bearer ${CONFIG.adminToken}`,
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`请求失败 ${endpoint}: ${response.status} ${text}`);
  }

  return response.json();
}

// 创建分类
async function createCategory() {
  try {
    console.log('创建大类:', CONFIG.categoryName);
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
  } catch (error) {
    if (error.message.includes('已存在')) {
      console.log('✓ 大类已存在，跳过');
    } else {
      throw error;
    }
  }
}

// 创建子类
async function createSubCategory() {
  try {
    console.log('创建子类:', CONFIG.subCategoryName);
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
  } catch (error) {
    if (error.message.includes('已存在')) {
      console.log('✓ 子类已存在，跳过');
    } else {
      throw error;
    }
  }
}

// 读取manifest.jsonl并筛选唐诗三百首
function loadTang300() {
  console.log('读取manifest.jsonl...');
  const content = fs.readFileSync(CONFIG.manifestPath, 'utf8');
  const lines = content.trim().split('\n');

  const tang300 = [];
  for (const line of lines) {
    try {
      const item = JSON.parse(line);
      if (item.type && item.type.includes('唐诗三百首')) {
        tang300.push(item);
      }
    } catch {}
  }

  console.log(`✓ 找到 ${tang300.length} 首唐诗三百首`);
  return tang300;
}

// 上传单首歌曲
async function uploadSong(poem) {
  const id = `tang300_${poem.id}`;

  // 构建音频文件路径
  const audioFilename = `${poem.title}-${poem.author}-${poem.id}.mp3`;
  const audioPath = path.join(CONFIG.audioDir, audioFilename);

  // 检查音频文件是否存在
  if (!fs.existsSync(audioPath)) {
    console.log(`⚠ 音频文件不存在: ${audioFilename}`);
    return false;
  }

  // 读取LRC歌词
  let lyric = '';
  const lrcPath = path.join(CONFIG.audioDir, `${poem.title}-${poem.author}-${poem.id}.lrc`);
  if (fs.existsSync(lrcPath)) {
    lyric = fs.readFileSync(lrcPath, 'utf8');
  }

  // 创建FormData
  const form = new FormData();
  form.append('id', id);
  form.append('name', poem.title);
  form.append('artist', poem.author);
  form.append('category_id', CONFIG.categoryId);
  form.append('sub_category_id', CONFIG.subCategoryId);
  form.append('audio', fs.createReadStream(audioPath));
  if (lyric) {
    form.append('lyric', lyric);
  }

  try {
    await request('/api/admin/songs', {
      method: 'POST',
      body: form,
      headers: form.getHeaders(),
    });
    return true;
  } catch (error) {
    if (error.message.includes('已存在')) {
      return true; // 已存在也算成功
    }
    console.log(`✗ 上传失败 ${poem.title}: ${error.message}`);
    return false;
  }
}

// 主函数
async function main() {
  console.log('=== 唐诗三百首导入工具 ===\n');

  // 校验必填配置
  const missing = [];
  if (!CONFIG.adminToken) missing.push('IMPORT_ADMIN_TOKEN');
  if (!CONFIG.manifestPath) missing.push('IMPORT_MANIFEST');
  if (!CONFIG.audioDir) missing.push('IMPORT_AUDIO_DIR');
  if (missing.length > 0) {
    console.error(`缺少环境变量: ${missing.join(', ')}`);
    process.exit(1);
  }

  try {
    // 1. 创建分类
    await createCategory();
    await createSubCategory();

    // 2. 加载数据
    const poems = loadTang300();

    // 3. 上传歌曲
    console.log('\n开始上传歌曲...');
    let success = 0;
    let failed = 0;

    for (let i = 0; i < poems.length; i++) {
      const poem = poems[i];
      const progress = `[${i + 1}/${poems.length}]`;

      process.stdout.write(`${progress} ${poem.title} - ${poem.author}...`);

      const ok = await uploadSong(poem);
      if (ok) {
        console.log(' ✓');
        success++;
      } else {
        console.log(' ✗');
        failed++;
      }

      // 每10首休息一下，避免请求过快
      if ((i + 1) % 10 === 0) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    console.log('\n=== 导入完成 ===');
    console.log(`成功: ${success} 首`);
    console.log(`失败: ${failed} 首`);

  } catch (error) {
    console.error('导入失败:', error);
    process.exit(1);
  }
}

// 运行
main();
