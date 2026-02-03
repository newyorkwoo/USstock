/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bull-red': '#C53D43',      /* 朱色 */
        'bear-green': '#3A5F3A',    /* 松葉色 */
        'jp': {
          'white': '#FAFAF8',
          'paper': '#F5F5F0',
          'ink': '#2D2D2D',
          'ink-light': '#5C5C5C',
          'red': '#C53D43',
          'green': '#3A5F3A',
          'blue': '#2E4A62',
          'gold': '#C49A00',
          'border': '#E8E4D9',
          'hover': '#F0EDE4',
        }
      },
      fontFamily: {
        'jp': ['Noto Sans TC', 'Hiragino Sans', 'Meiryo', 'sans-serif'],
        'jp-serif': ['Noto Serif TC', 'Hiragino Mincho ProN', 'serif'],
      },
      fontSize: {
        'jp-xs': ['14px', '1.6'],
        'jp-sm': ['15px', '1.7'],
        'jp-base': ['17px', '1.8'],
        'jp-lg': ['19px', '1.7'],
        'jp-xl': ['22px', '1.6'],
        'jp-2xl': ['26px', '1.5'],
        'jp-3xl': ['32px', '1.4'],
      },
      borderRadius: {
        'jp': '2px',
      },
      boxShadow: {
        'jp': '0 1px 3px rgba(0, 0, 0, 0.04)',
        'jp-hover': '0 2px 8px rgba(0, 0, 0, 0.08)',
      }
    },
  },
  plugins: [],
}
