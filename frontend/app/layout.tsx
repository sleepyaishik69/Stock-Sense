import './globals.css';
import type { Metadata } from 'next';
import { Geist } from 'next/font/google';

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' });

export const metadata: Metadata = { title: 'StockSense AI | Retail intelligence', description: 'Retail performance, inventory and purchasing insights, grounded in your data.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en" className={geist.variable}><body>{children}</body></html>; }
