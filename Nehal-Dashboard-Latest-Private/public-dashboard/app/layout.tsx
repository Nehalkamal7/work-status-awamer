import type {Metadata} from "next";
import "./globals.css";
import OdooUpdatesPanel from "./OdooUpdatesPanel";
import WhatsAppUpdatesPanel from "./WhatsAppUpdatesPanel";
import DailyPlanPanel from "./DailyPlanPanel";
import WeeklyReportPanel from "./WeeklyReportPanel";
export const metadata:Metadata={title:"لوحة متابعة نهال كمال",description:"تقرير للقراءة فقط عن حالة المهام والمشروعات الحالية"};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="ar" dir="rtl"><body>{children}<DailyPlanPanel/><WhatsAppUpdatesPanel/><WeeklyReportPanel/><OdooUpdatesPanel/></body></html>}
