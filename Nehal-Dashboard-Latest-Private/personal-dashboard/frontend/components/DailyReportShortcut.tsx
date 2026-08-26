"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
export default function DailyReportShortcut(){const path=usePathname();if(path==="/login"||path==="/whatsapp-report")return null;return <Link href="/whatsapp-report" className="fixed bottom-5 left-5 z-50 rounded-2xl bg-[#1f8f5f] px-5 py-3 text-sm font-black text-white shadow-xl hover:bg-[#18764e]">تقرير محادثات اليوم</Link>}
