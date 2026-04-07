/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sand: '#f7efe0',
        ink: '#1f1c17',
        ember: '#ba5b34',
        moss: '#5b6b43'
      },
      fontFamily: {
        display: ['Georgia', 'serif'],
        body: ['Segoe UI', 'sans-serif']
      }
    }
  },
  plugins: []
}
