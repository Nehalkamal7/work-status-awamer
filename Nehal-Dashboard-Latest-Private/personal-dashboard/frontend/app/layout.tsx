import "./globals.css";
import Providers from "./providers";
import DailyReportShortcut from "@/components/DailyReportShortcut";
import DailyPlanShortcut from "@/components/DailyPlanShortcut";
export const metadata={title:"لوحة نهال الخاصة",description:"إدارة وتعديل المشاريع والتقارير اليومية"};
export default function Root({children}:{children:React.ReactNode}){return <html lang="ar" dir="rtl"><body><Providers>{children}<DailyPlanShortcut/><DailyReportShortcut/></Providers></body></html>}
