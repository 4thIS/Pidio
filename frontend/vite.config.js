import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 빌드 산출물은 백엔드 정적 폴더로, 개발 시 /api·/stream·/events 는 백엔드로 프록시
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../backend/app/static',
    emptyOutDir: false,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/stream': 'http://localhost:8000',
      '/thumb': 'http://localhost:8000',
      '/events': 'http://localhost:8000',
    },
  },
})
