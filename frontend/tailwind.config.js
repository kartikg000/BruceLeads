
/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "#09090b", // Deep black
                surface: "#18181b",    // Zinc 900
                primary: "#fafafa",    // White text
                secondary: "#a1a1aa",  // Zinc 400
                accent: "#2563eb",     // Blue
                border: "#27272a",     // Zinc 800
            }
        },
    },
    plugins: [],
}
