import './globals.css'

export const metadata = {
  title: 'Omaha Estate Sale Hunter',
  description: 'Discover and grade estate sales in the Omaha metro area',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
