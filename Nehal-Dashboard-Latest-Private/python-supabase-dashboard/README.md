# Python + Supabase Rebuilt Dashboard (Command Center)

Complete, modular Python rebuild of Nehal's Project Command Center dashboard powered by **Supabase (PostgreSQL)** backend and **Streamlit + Plotly** frontend.

## 📁 Repository Structure

```
python-supabase-dashboard/
├── supabase_schema.sql     # Complete PostgreSQL SQL migration script for Supabase
├── .env.example            # Environment variables template
├── requirements.txt        # Required Python packages
├── supabase_client.py      # Supabase connection manager & error handling
├── queries.py              # Isolated DB functions, pagination, & RPC aggregations
├── app.py                  # Dynamic Streamlit + Plotly RTL Dashboard UI
└── README.md
```

## 🚀 Quick Setup Instructions

### Step 1: Execute SQL Migration in Supabase
1. Open your [Supabase Dashboard](https://supabase.com/dashboard).
2. Go to **SQL Editor**.
3. Copy the contents of [`supabase_schema.sql`](file:///c:/yarab/work%20status%20awamer/Nehal-Dashboard-Latest-Private/python-supabase-dashboard/supabase_schema.sql) and paste them into the SQL Editor.
4. Click **Run**. This will set up:
   - Tables (`users`, `projects`, `tasks`, `integrations`, `sync_logs`, `notifications`, `workday_plans`, `sync_conflicts`, `activities`).
   - Indexes and PostgreSQL Triggers.
   - Database-level aggregation RPC functions (`get_dashboard_kpis()`).
   - Row-Level Security (RLS) policies.

### Step 2: Configure Environment Variables
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in your Supabase project credentials:
   ```env
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_KEY=your-supabase-anon-or-service-key
   ```

### Step 3: Install Dependencies & Run Dashboard
```bash
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## ✨ Key Features & Optimizations

- **Full Functional Parity**: Full RTL support, project tracking across the 6 workflow stages (`التحليل`, `التصميم`, `البرمجة`, `الاختبار والمراجعة`, `التسليم`, `الدعم الفني`), urgent vs stable categorization, daily report management, and inline editing.
- **Optimized SQL Queries**: Database aggregation via server-side RPC stored procedure (`get_dashboard_kpis`), server-side text searching, filtering, and paginated range fetches to prevent loading raw data into client memory.
- **Robust Error Handling**: Connection probes, fallback calculations, and graceful error alerts when database credentials or tables are uninitialized.
- **Interactive Visualizations**: Reactive Plotly charts for stage distribution and progress monitoring.
