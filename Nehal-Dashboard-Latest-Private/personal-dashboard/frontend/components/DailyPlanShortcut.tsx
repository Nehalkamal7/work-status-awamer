"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
export default function DailyPlanShortcut(){const path=usePathname();if(path==="/login"||path==="/daily-plan")return null;return <Link href="/daily-plan" className="fixed bottom-20 left-5 z-50 rounded-2xl bg-[#e6a72b] px-5 py-3 text-sm font-black text-ink shadow-xl hover:bg-[#d39722]">مشاريع اليوم</Link>}
