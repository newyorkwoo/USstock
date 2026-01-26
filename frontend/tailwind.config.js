/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bull-red': '#ef4444',
        'bear-green': '#22c55e',
      }
    },
  },
  plugins: [],
}
