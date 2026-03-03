/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
  ],
  safelist: [
    'bg-gray-500',
    'bg-blue-500',
    'bg-yellow-500',
    'bg-orange-500',
    'bg-purple-500',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0f172a',
        accent: '#1e40af',
        'accent-hover': '#172554',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        heading: ['Outfit', 'system-ui', 'sans-serif'],
      }
    }
  },
  plugins: [],
}
