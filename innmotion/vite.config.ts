import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import basicSsl from '@vitejs/plugin-basic-ssl';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    tailwindcss(),
    // `npm run dev:https` – lokales Zertifikat, damit die Kamera auch auf einem Handy im WLAN funktioniert.
    ...(mode === 'https' ? [basicSsl()] : []),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: { enabled: true, type: 'module' },
      includeAssets: ['icon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'INNmotion – Sport & Freizeit im Internat',
        short_name: 'INNmotion',
        description: 'Mitmachen, Punkte sammeln, gemeinsam als Standort-Team gewinnen.',
        lang: 'de',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#0B0D10',
        theme_color: '#0B0D10',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        navigateFallback: '/index.html',
      },
    }),
  ],
  test: { include: ['src/**/*.test.ts'] },
}));
