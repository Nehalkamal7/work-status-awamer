# Nehal's Command Center Dashboard (Vercel + Supabase Python)

Complete, modular Python rebuild of Nehal's Project Command Center dashboard designed for **Vercel Serverless Functions** backed by **Supabase (PostgreSQL)**.

## 📁 Repository Structure

```
Nehal-Dashboard-Latest-Private/
├── vercel.json             # Vercel Serverless Function deployment config
├── requirements.txt        # Python dependencies (fastapi, supabase, uvicorn, jinja2)
├── .env.example            # Environment variables template
├── supabase_schema.sql     # PostgreSQL SQL migration script for Supabase SQL Editor
├── api/
│   └── index.py            # FastAPI entrypoint & Supabase database queries
├── templates/
│   ├── dashboard.html      # Glassmorphic RTL dashboard UI with modal forms
│   └── project_card.html   # Reusable project card component
└── README.md
```

## 🚀 Quick Vercel Deployment Instructions

### Method A: Deploy via Vercel CLI (Recommended)

1. Open your terminal in this repository folder:
   ```powershell
   cd "c:\yarab\work status awamer\Nehal-Dashboard-Latest-Private"
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

1. Push this clean repository to GitHub.
2. Log into [Vercel Dashboard](https://vercel.com/new) -> **Import Repository**.
3. Under **Environment Variables**, add:
   - `SUPABASE_URL` = `https://your-project-id.supabase.co`
   - `SUPABASE_KEY` = `your-supabase-anon-or-service-key`
4. Click **Deploy**. Vercel will automatically build the Python app and give you a live production URL!

---

## 📊 Database Setup

Before deploying, ensure you have executed [`supabase_schema.sql`](file:///c:/yarab/work%20status%20awamer/Nehal-Dashboard-Latest-Private/supabase_schema.sql) in your **Supabase SQL Editor** to create all tables, indexes, RLS policies, and server-side RPC functions (`get_dashboard_kpis()`).
