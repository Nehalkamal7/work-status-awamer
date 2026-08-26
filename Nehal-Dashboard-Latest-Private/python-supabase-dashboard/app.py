import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from supabase_client import check_db_health, get_supabase_client
from queries import (
    fetch_dashboard_kpis,
    fetch_projects,
    create_project,
    update_project,
    delete_project,
    fetch_tasks_by_project
)

# Page configuration
st.set_page_config(
    page_title="لوحة متابعة مشاريعي | Nehal Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design & RTL Support
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }

    /* Custom Header Banner */
    .header-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 24px;
        padding: 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    .badge-lime {
        background-color: rgba(163, 230, 53, 0.15);
        color: #a3e635;
        font-size: 13px;
        font-weight: 900;
        padding: 4px 12px;
        border-radius: 9999px;
        letter-spacing: 0.05em;
    }

    /* Metric Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 16px 20px;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #a3e635;
    }
    .metric-label {
        color: rgba(255, 255, 255, 0.65);
        font-size: 13px;
        font-weight: 600;
    }
    .metric-val {
        font-size: 32px;
        font-weight: 900;
        color: #ffffff;
        margin-top: 4px;
    }

    /* Project Cards */
    .project-card {
        background: #1e293b;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .daily-report-box {
        background-color: #0f172a;
        border-radius: 12px;
        padding: 14px;
        border-right: 4px solid #ef4444;
        margin-top: 12px;
    }

    /* Stage Colors */
    .stage-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 14px;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
        font-family: 'Cairo', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Constants & Stages Config
STAGES = ["التحليل", "التصميم", "البرمجة", "الاختبار والمراجعة", "التسليم", "الدعم الفني"]
STAGE_COLORS = {
    "التحليل": "#7667d8",
    "التصميم": "#d46a98",
    "البرمجة": "#247f75",
    "الاختبار والمراجعة": "#d68a21",
    "التسليم": "#3975bd",
    "الدعم الفني": "#718076"
}

def stage_of(status: str) -> str:
    v = (status or "").lower()
    if "تحليل" in v or "analysis" in v: return STAGES[0]
    if "تصميم" in v or "design" in v: return STAGES[1]
    if "برمج" in v or "development" in v or "programming" in v: return STAGES[2]
    if "تيست" in v or "اختبار" in v or "testing" in v or "review" in v: return STAGES[3]
    if "تسليم" in v or "delivery" in v: return STAGES[4]
    return STAGES[5]

# Main Application Logic
def main():
    # 1. Connection Probe & Notice
    db_connected = check_db_health()

    if not db_connected:
        st.warning("⚠️ لم يتم الاتصال بقاعدة بيانات Supabase. يرجى التأكد من ضبط متغيرات البيئة `.env` (`SUPABASE_URL` & `SUPABASE_KEY`) وتشغيل ملف الترحيل `supabase_schema.sql` في Supabase SQL Editor.")
        st.info("💡 يمكنك الاستمرار في استعراض الواجهة في وضع المعاينة المحلية.")
    
    # 2. Header Banner & KPIs
    st.markdown("""
    <div class="header-banner">
        <span class="badge-lime">مساحة نهال الخاصة · Supabase + Python</span>
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 12px; flex-wrap: wrap;">
            <div>
                <h1 style="font-size: 36px; font-weight: 900; margin: 0; color: #ffffff;">لوحة متابعة مشاريعي (Command Center)</h1>
                <p style="color: rgba(255, 255, 255, 0.7); margin-top: 6px; font-size: 15px;">عدّلي الحالة والتواريخ والتقرير اليومي مباشرة وبسرعة فائقة عبر قاعدة بيانات Supabase.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch Database KPIs using optimized server-side RPC / Aggregation
    kpis = fetch_dashboard_kpis()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">إجمالي المشاريع</div>
            <div class="metric-val">{kpis.get('total_projects', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">أولوية ومتابعة عاجلة</div>
            <div class="metric-val" style="color: #f87171;">{kpis.get('urgent_projects', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">لها تقرير يومي</div>
            <div class="metric-val" style="color: #a3e635;">{kpis.get('has_daily_report', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">متوسط نسبة الإنجاز</div>
            <div class="metric-val" style="color: #38bdf8;">{kpis.get('avg_progress', 0)}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Action Controls & Filters Bar
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([3, 2, 2, 2])
    
    with ctrl_col1:
        search_q = st.text_input("🔍 البحث في المشاريع", placeholder="ابحث باسم المشروع أو العميل أو الكود...", key="search_input")
    with ctrl_col2:
        stage_filter = st.selectbox("المرحلة الحالية", ["ALL"] + STAGES, index=0)
    with ctrl_col3:
        priority_filter = st.selectbox("الأولوية", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"], index=0)
    with ctrl_col4:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        show_add_modal = st.button("➕ إضافة مشروع جديد", type="primary", use_container_width=True)

    # 4. Fetch Projects based on Reactive Filters
    projects = fetch_projects(
        search_query=search_q,
        stage_filter=stage_filter,
        priority_filter=priority_filter
    )

    # 5. Charts & Visualizations Section
    if projects:
        df_projects = pd.DataFrame(projects)
        df_projects['stage_group'] = df_projects['status'].apply(stage_of)
        
        with st.expander("📊 التحليلات البصرية والرسوم البيانية", expanded=False):
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                stage_counts = df_projects['stage_group'].value_counts().reset_index()
                stage_counts.columns = ['المرحلة', 'عدد المشاريع']
                fig_pie = px.pie(
                    stage_counts, 
                    values='عدد المشاريع', 
                    names='المرحلة',
                    title="توزيع المشاريع حسب مراحل العمل",
                    color='المرحلة',
                    color_discrete_map=STAGE_COLORS,
                    hole=0.4
                )
                fig_pie.update_layout(template="plotly_dark", font_family="Cairo")
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with chart_col2:
                fig_bar = px.bar(
                    df_projects,
                    x='name',
                    y='progress',
                    color='stage_group',
                    color_discrete_map=STAGE_COLORS,
                    title="نسبة إنجاز المشاريع الحالية (%)",
                    labels={'name': 'المشروع', 'progress': 'نسبة الإنجاز %', 'stage_group': 'المرحلة'}
                )
                fig_bar.update_layout(template="plotly_dark", font_family="Cairo", yaxis_range=[0, 100])
                st.plotly_chart(fig_bar, use_container_width=True)

    # 6. Add/Edit Project Modal Expander
    if show_add_modal or "editing_project_id" in st.session_state:
        st.markdown("### 📝 " + ("تعديل بيانات المشروع" if "editing_project_id" in st.session_state else "إضافة مشروع جديد"))
        
        edit_item = None
        if "editing_project_id" in st.session_state:
            edit_item = next((p for p in projects if p['id'] == st.session_state["editing_project_id"]), None)

        with st.form("project_form", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                p_name = st.text_input("اسم المشروع *", value=edit_item.get("name", "") if edit_item else "")
                p_client = st.text_input("العميل", value=edit_item.get("client", "") if edit_item else "")
                p_status = st.selectbox("مرحلة العمل", STAGES, index=STAGES.index(stage_of(edit_item.get("status", "التحليل"))) if edit_item else 0)
                p_priority = st.selectbox("الأولوية", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], index=["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(edit_item.get("priority", "MEDIUM")) if edit_item else 2)
                p_assigned = st.text_input("المسؤول", value=edit_item.get("assigned_to", "") if edit_item else "")
            
            with f_col2:
                p_start = st.date_input("تاريخ البداية", value=datetime.strptime(edit_item["start_date"], "%Y-%m-%d") if edit_item and edit_item.get("start_date") else None)
                p_deadline = st.date_input("موعد التسليم (Deadline)", value=datetime.strptime(edit_item["deadline"], "%Y-%m-%d") if edit_item and edit_item.get("deadline") else None)
                p_progress = st.slider("نسبة الإنجاز %", 0, 100, int(edit_item.get("progress", 0)) if edit_item else 0)
                p_source_id = st.text_input("كود / معرف المصدر (Odoo / Google Sheet)", value=edit_item.get("source_id", "") if edit_item else "")

            p_daily_report = st.text_area("التقرير اليومي", value=edit_item.get("daily_report", "") if edit_item else "", rows=3)
            p_desc = st.text_area("ملاحظات ووصف المشروع", value=edit_item.get("description", "") if edit_item else "", rows=3)

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                submitted = st.form_submit_button("💾 حفظ المشروع", type="primary", use_container_width=True)
            with btn_col2:
                cancel = st.form_submit_button("إلغاء", use_container_width=True)

            if cancel:
                if "editing_project_id" in st.session_state:
                    del st.session_state["editing_project_id"]
                st.rerun()

            if submitted:
                if not p_name.strip():
                    st.error("اسم المشروع مطلوب!")
                else:
                    payload = {
                        "name": p_name.strip(),
                        "client": p_client.strip(),
                        "status": p_status,
                        "priority": p_priority,
                        "assigned_to": p_assigned.strip(),
                        "start_date": str(p_start) if p_start else None,
                        "deadline": str(p_deadline) if p_deadline else None,
                        "progress": float(p_progress),
                        "source_id": p_source_id.strip(),
                        "daily_report": p_daily_report.strip(),
                        "description": p_desc.strip()
                    }
                    try:
                        if edit_item:
                            update_project(edit_item["id"], payload)
                            st.success("تم تحديث المشروع بنجاح!")
                            del st.session_state["editing_project_id"]
                        else:
                            create_project(payload)
                            st.success("تمت إضافة المشروع بنجاح!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"تعذر حفظ المشروع: {str(ex)}")

    # 7. Project Categorization Rendering (Urgent vs Stable)
    if not projects:
        st.info("لا توجد مشاريع مطابقة للبحث أو التصفية الحالية.")
    else:
        urgent_projects = [p for p in projects if p.get("priority") in ["CRITICAL", "HIGH"]]
        stable_projects = [p for p in projects if p not in urgent_projects]

        # Urgent Section
        st.markdown("### 🔥 الأهم أولًا - أولوية ومتابعة عاجلة")
        render_stage_groups(urgent_projects)

        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 36px 0;'>", unsafe_allow_html=True)

        # Stable Section
        st.markdown("### 📌 المشاريع المستقرة حسب المرحلة")
        render_stage_groups(stable_projects)

def render_stage_groups(project_list: List[dict]):
    if not project_list:
        st.caption("لا توجد مشاريع في هذه الفئة.")
        return

    for stage in STAGES:
        stage_items = [p for p in project_list if stage_of(p.get("status", "")) == stage]
        if not stage_items:
            continue

        color = STAGE_COLORS[stage]
        st.markdown(f"""
        <div style="border-right: 6px solid {color}; background: {color}15; padding: 12px 18px; border-radius: 12px; margin: 16px 0;">
            <span style="color: rgba(255,255,255,0.7); font-size: 13px;">مرحلة العمل</span>
            <h3 style="margin: 0; color: #ffffff; font-weight: 900;">{stage} ({len(stage_items)} مشروع)</h3>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(2)
        for idx, p in enumerate(stage_items):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"""
                    <div class="project-card" style="border-top: 4px solid {color};">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <small style="color: #94a3b8; font-weight: 700;">{p.get('source_id') or p.get('source', 'LOCAL')}</small>
                                <h4 style="margin: 4px 0 0 0; font-size: 20px; color: #ffffff;">{p.get('name')}</h4>
                                <small style="color: #cbd5e1;">العميل: {p.get('client') or 'غير محدد'}</small>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 16px 0; font-size: 13px;">
                            <div><b>موعد التسليم:</b> {p.get('deadline') or 'غير محدد'}</div>
                            <div><b>الأولوية:</b> <span style="color: {'#ef4444' if p.get('priority')=='CRITICAL' else '#f97316' if p.get('priority')=='HIGH' else '#3b82f6'};">{p.get('priority')}</span></div>
                            <div><b>نسبة الإنجاز:</b> {p.get('progress')}%</div>
                            <div><b>المسؤول:</b> {p.get('assigned_to') or 'غير محدد'}</div>
                        </div>
                        <div class="daily-report-box">
                            <small style="color: #ef4444; font-weight: 900;">📝 التقرير اليومي:</small>
                            <p style="margin: 6px 0 0 0; font-size: 13px; color: #e2e8f0; white-space: pre-wrap;">{p.get('daily_report') or 'لم يُكتب تقرير اليوم بعد.'}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    b_col1, b_col2 = st.columns([1, 1])
                    with b_col1:
                        if st.button("✏️ تعديل", key=f"edit_{p['id']}", use_container_width=True):
                            st.session_state["editing_project_id"] = p["id"]
                            st.rerun()
                    with b_col2:
                        if st.button("🗑️ حذف", key=f"del_{p['id']}", use_container_width=True):
                            if delete_project(p["id"]):
                                st.success("تم الحذف بنجاح!")
                                st.rerun()

if __name__ == "__main__":
    main()
