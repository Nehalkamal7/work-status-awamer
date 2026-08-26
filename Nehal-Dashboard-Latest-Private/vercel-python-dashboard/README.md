# Deploying Nehal's Command Center Dashboard to Vercel (Python + Supabase)

This directory contains the **Vercel Serverless Python** build of Nehal's Project Command Center dashboard using **FastAPI + Jinja2 + Supabase (PostgreSQL)**.

## 🚀 Why this works on Vercel
Streamlit requires persistent server processes and WebSocket connections which are not supported on serverless platforms like Vercel. 
This implementation uses **FastAPI Serverless Functions** (`@vercel/python`) which load instantly, scale automatically, and run 100% natively on Vercel!

---

## 🛠️ Step-by-Step Vercel Deployment

### Method A: Deploy via Vercel CLI (Fastest)

1. Open your terminal in this directory:
   ```bash
   cd "c:\yarab\work status awamer\Nehal-Dashboard-Latest-Private\vercel-python-dashboard"
   ```

2. Run `vercel` (or `npx vercel`):
   ```bash
   npx vercel
   ```

3. Set your Environment Variables in Vercel:
   - `SUPABASE_URL`: `https://your-project-id.supabase.co`
   - `SUPABASE_KEY`: `your-supabase-anon-or-service-key`

4. Run production deployment:
   ```bash
   npx vercel --prod
   ```

---

### Method B: Deploy via GitHub / Vercel Web Dashboard

1. Push this folder to your GitHub repository.
2. Log into [Vercel Dashboard](https://vercel.com/new).
3. Select your repository.
4. Set the **Root Directory** to `vercel-python-dashboard`.
5. Under **Environment Variables**, add:
   - `SUPABASE_URL` = `https://your-project-ref.supabase.co`
   - `SUPABASE_KEY` = `your-anon-or-service-role-key`
6. Click **Deploy**. Vercel will automatically build the `@vercel/python` app and give you a live production URL!

---

## 📊 Database Setup Reminder

Make sure you ran the SQL schema migration script [`supabase_schema.sql`](file:///c:/yarab/work%20status%20awamer/Nehal-Dashboard-Latest-Private/python-supabase-dashboard/supabase_schema.sql) in your **Supabase SQL Editor** so all tables, indexes, RLS policies, and server-side RPC functions exist.
