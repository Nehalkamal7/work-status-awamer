"use client";

import {useEffect,useState} from "react";
import "./source-sync.css";

type SourceKey="odoo"|"sheet"|"whatsapp";
type SourceState={status:"loading"|"live"|"error";updatedAt:string};
const initial:Record<SourceKey,SourceState>={odoo:{status:"loading",updatedAt:""},sheet:{status:"loading",updatedAt:""},whatsapp:{status:"loading",updatedAt:""}};
const sources:Array<{key:SourceKey;title:string;description:string}>=[
  {key:"odoo",title:"Odoo",description:"تحديثات المشروعات وLog Notes"},
  {key:"sheet",title:"Google Sheets الخاص بي",description:"الحالات والتواريخ المسجلة في الشيت"},
  {key:"whatsapp",title:"WhatsApp Business",description:"محادثات ومتابعات جروبات المشروعات"}
];

export default function SourceSyncPanel({onDashboardRefresh}:{onDashboardRefresh:()=>Promise<void>}){
  const[state,setState]=useState(initial);
  const[updatingAll,setUpdatingAll]=useState(false);
  async function updateSource(key:SourceKey,refreshDashboard=true){
    setState(current=>({...current,[key]:{...current[key],status:"loading"}}));
    try{
      if(key==="sheet"){
        const response=await fetch(`/api/google-sheet?_=${Date.now()}`,{cache:"no-store"});
        const data=await response.json() as {projects?:unknown[];syncedAt?:string};
        if(!response.ok||!Array.isArray(data.projects))throw new Error("sheet");
        if(refreshDashboard)await onDashboardRefresh();
        setState(current=>({...current,sheet:{status:"live",updatedAt:data.syncedAt||new Date().toISOString()}}));
        return;
      }
      const endpoint=key==="odoo"?"/api/odoo?period=day":"/api/whatsapp?period=day";
      const response=await fetch(`${endpoint}&_=${Date.now()}`,{cache:"no-store"});
      const data=await response.json() as {projects?:unknown[];updates?:unknown[];syncedAt?:string};
      const valid=key==="odoo"?Array.isArray(data.projects):Array.isArray(data.updates);
      if(!response.ok||!valid)throw new Error(key);
      if(key==="odoo"&&refreshDashboard)await onDashboardRefresh();
      setState(current=>({...current,[key]:{status:"live",updatedAt:data.syncedAt||new Date().toISOString()}}));
    }catch{setState(current=>({...current,[key]:{...current[key],status:"error"}}))}
  }
  async function updateAll(){setUpdatingAll(true);try{await Promise.all((Object.keys(initial) as SourceKey[]).map(key=>updateSource(key,false)));await onDashboardRefresh()}finally{setUpdatingAll(false)}}
  useEffect(()=>{void updateAll();const timer=setInterval(()=>void updateAll(),60000);return()=>clearInterval(timer)},[]);
  const values=Object.values(state),hasError=values.some(item=>item.status==="error"),latest=values.map(item=>item.updatedAt).filter(Boolean).sort().at(-1);
  return <section className={`sourceSync combined ${hasError?"error":"live"}`} aria-label="تحديث كل مصادر البيانات"><div className="combinedSource"><i/><div><span>اتصال مباشر موحّد</span><h2>Odoo + Google Sheets + WhatsApp</h2><small>{updatingAll?"جاري تحديث المصادر الثلاثة…":hasError?"تم التحديث مع تعذّر مصدر مؤقتًا":"المصادر الثلاثة مباشرة — تحديث تلقائي كل دقيقة"}{latest&&` · آخر تحديث ${new Date(latest).toLocaleTimeString("ar-EG",{hour:"2-digit",minute:"2-digit"})}`}</small></div></div><button type="button" onClick={()=>void updateAll()} disabled={updatingAll}>{updatingAll?"جاري التحديث…":"تحديث الكل الآن"}</button></section>
}
