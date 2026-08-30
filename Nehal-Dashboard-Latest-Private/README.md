# Nehal's Command Center Dashboard (Vercel + Supabase Python)

Complete, modular Python rebuild of Nehal's Project Command Center dashboard designed for **Vercel Serverless Functions** backed by **Supabase (PostgreSQL)**.

## 📁 Repository Structure

```
.
├── vercel.json             # Vercel Serverless Function deployment config
├── requirements.txt        # Python dependencies (fastapi, supabase, uvicorn, jinja2, websockets)
├── .env.example            # Environment variables template
├── supabase_schema.sql     # PostgreSQL SQL migration script for Supabase SQL Editor
├── api/
│   └── index.py            # FastAPI entrypoint, database client singleton & REST endpoints
├── templates/
│   ├── dashboard.html      # Glassmorphic RTL dashboard UI with modal forms & interactive KPIs
│   └── project_card.html   # Reusable project card component with stage badges & progress bars
└── README.md
```

## 🚀 Key Features

- **Glassmorphic RTL UI**: Beautiful dark mode aesthetic styled with Cairo typography and smooth micro-animations.
- **Interactive KPI Metrics**: Quick filter projects by Urgent, Completed, or Daily Report status with a single click.
- **Stage Pills & Progress Visuals**: Visual stage badges ("التحليل", "التصميم", "البرمجة", "الاختبار والمراجعة", "التسليم", "الدعم الفني") and dynamic progress bar colors.
- **Pydantic Validation**: Sanitized date input handling (`""` to `None`) and float range clamping to prevent PostgreSQL errors.
- **Safe JS Data Binding**: Prevents quotes and multi-line breaks in reports from crashing modal popups.
- **Toast Notifications**: Interactive feedback on saving, updating, and deleting projects.

## 🚀 Quick Vercel Deployment Instructions

### Method A: Deploy via Vercel CLI (Recommended)

1. Open your terminal in this repository folder:
   ```powershell
   cd "c:\yarab\work status awamer"
   ```

2. Run `vercel`:
   ```bash
   npx vercel
   ```

3. When prompted in the CLI, add your **Supabase Environment Variables**:
   - `SUPABASE_URL` = `https://your-project-id.supabase.co`
   - `SUPABASE_KEY` = `your-supabase-anon-or-service-key`

4. Deploy to production:
   ```bash
   npx vercel --prod
   ```

---

### Method B: Deploy via GitHub & Vercel Dashboard

1. Push this repository to GitHub.
2. Log into [Vercel Dashboard](https://vercel.com/new) -> **Import Repository**.
3. Under **Environment Variables**, add:
   - `SUPABASE_URL` = `https://your-project-id.supabase.co`
   - `SUPABASE_KEY` = `your-supabase-anon-or-service-key`
4. Click **Deploy**. Vercel will automatically build the Python app and give you a live production URL!

---

## 📊 Database Setup

Before deploying, ensure you have executed [`supabase_schema.sql`](file:///c:/yarab/work%20status%20awamer/supabase_schema.sql) in your **Supabase SQL Editor** to create all tables, indexes, RLS policies, and server-side RPC functions (`get_dashboard_kpis()`).
