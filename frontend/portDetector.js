import net from 'net';
import fs from 'fs';

// 動態檢測可用端口
function checkPort(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    
    server.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        resolve(false);
      }
    });
    
    server.once('listening', () => {
      server.close();
      resolve(true);
    });
    
    server.listen(port);
  });
}

async function findAvailablePort(startPort = 3000, endPort = 3100) {
  for (let port = startPort; port <= endPort; port++) {
    const isAvailable = await checkPort(port);
    if (isAvailable) {
      return port;
    }
  }
  throw new Error('No available port found');
}

// 主程序
(async () => {
  try {
    const port = await findAvailablePort(3000, 3100);
    console.log(`✓ 找到可用端口: ${port}`);
    
    // 更新 vite.config.js 中的端口
    const viteConfig = `import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: ${port},
    host: true
  }
})
`;
    
    fs.writeFileSync('vite.config.js', viteConfig);
    console.log(`✓ Vite 配置已更新，使用端口: ${port}`);
  } catch (error) {
    console.error('端口檢測錯誤:', error);
    process.exit(1);
  }
})();
