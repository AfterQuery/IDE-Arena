import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AfterQuery IDE Arena',
  description: 'AfterQuery IDE Arena',
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
