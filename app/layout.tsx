import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AfterQuery IDE Arena Traces',
  description: 'AfterQuery IDE Arena Traces',
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
