/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        // Define a tactical, high-readability monospace stack
        mono: [
          'JetBrains Mono', 
          'Fira Code', 
          'ui-monospace', 
          'SFMono-Regular', 
          'Menlo', 
          'Monaco', 
          'Consolas', 
          '"Liberation Mono"', 
          '"Courier New"', 
          'monospace'
        ],
        sans: ['Inter', 'Geist Sans', 'sans-serif'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        fact: "hsl(var(--fact))",
        formula: "hsl(var(--formula))",
        plan: "hsl(var(--plan))",
        
        // Extend the slate palette for deeper, darker backgrounds
        slate: {
          950: '#020617', // A darker slate for the main app background
        },
        // Define custom "glowing" colors for high-confidence states
        emerald: {
          'glow': '#10b981', // A bright emerald for the frozen state glow
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
          950: '#022c22',
        },
        blue: {
          'glow': '#3b82f6', // A bright blue for the forming state glow
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      backgroundImage: {
        // Create a subtle "redacted" or "X-pattern" gradient for the 'KILLED' state
        'killed-gradient': 'linear-gradient(45deg, transparent 45%, rgba(220, 38, 38, 0.1) 45%, rgba(220, 38, 38, 0.1) 55%, transparent 55%), linear-gradient(-45deg, transparent 45%, rgba(220, 38, 38, 0.1) 45%, rgba(220, 38, 38, 0.1) 55%, transparent 55%)',
      },
      boxShadow: {
        // Define custom shadows to create a "glowing" effect for active nodes
        'glow-emerald': '0 0 15px -3px rgba(16, 185, 129, 0.4), 0 0 6px -2px rgba(16, 185, 129, 0.2)',
        'glow-blue': '0 0 15px -3px rgba(59, 130, 246, 0.4), 0 0 6px -2px rgba(59, 130, 246, 0.2)',
      },
    },
  },
  plugins: [],
}
