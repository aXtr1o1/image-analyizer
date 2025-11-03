import './globals.css'

export const metadata = {
  title: 'Construction Safety Analyzer',
  description: 'AI-powered construction safety analysis',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}