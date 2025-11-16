# ✅ Tasks For You - Quick Checklist

## 🎯 **I've Done Everything I Can!**

Here's what I automated:
- ✅ Fixed database migration foreign key issue
- ✅ Created `.env` files for both agents
- ✅ Set up shared database credentials
- ✅ Created database setup SQL script
- ✅ Created integration test script
- ✅ Created startup batch files

---

## 📝 **What YOU Need to Do:**

### **🔑 STEP 1: Get Tavily API Key** (5 minutes)

**Why?** Tech Spec Agent needs this to research technology options.

1. Go to: https://tavily.com/
2. Click "Sign Up" (free tier available)
3. Get your API key
4. Open: `Tech Agent/.env`
5. Find line: `TAVILY_API_KEY=tvly-YOUR_TAVILY_API_KEY_HERE`
6. Replace with your real key

---

### **🗄️ STEP 2: Set Up Database** (5 minutes)

```bash
# Run this command:
psql -U postgres -f "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent\setup_database.sql"

# Enter your PostgreSQL password when asked
```

**What this does:**
- Creates `anyon_db` database
- Creates `anyon_user` with password `anyon_password_2025`
- Sets up schemas and permissions

---

### **📦 STEP 3: Install Dependencies** (10 minutes)

**Design Agent:**
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Tech Spec Agent:**
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

### **🔄 STEP 4: Run Database Migrations** (2 minutes)

**IMPORTANT: Run Design Agent FIRST!**

**Design Agent:**
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"
venv\Scripts\activate
alembic upgrade head
```

**Tech Spec Agent:**
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
venv\Scripts\activate
alembic upgrade head
```

---

### **🚀 STEP 5: Start Both Agents** (2 minutes)

**Terminal 1 - Design Agent:**
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Design Agent"
start_design_agent.bat
```

**Terminal 2 - Tech Spec Agent:**
```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
start_tech_spec_agent.bat
```

---

### **✅ STEP 6: Verify** (1 minute)

Test the health endpoint:

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

---

## 🎉 **That's It!**

**Total Time:** ~25 minutes

---

## ❓ **Need Help?**

**If something doesn't work:**

1. **PostgreSQL not running?**
   - Start it: `pg_ctl start`

2. **Redis not running?**
   - Start it: `redis-server`

3. **Can't find a command?**
   - Make sure you activated the virtual environment: `venv\Scripts\activate`

4. **Database error?**
   - Check credentials in `.env` files match
   - Make sure you ran `setup_database.sql`

5. **Foreign key error?**
   - Make sure you ran Design Agent migrations FIRST

---

## 📚 **Detailed Documentation**

- **SETUP_GUIDE.md** - Step-by-step setup instructions
- **INTEGRATION_CONFIGURATION_GUIDE.md** - Technical details

---

## 🧪 **Optional: Run Integration Test**

Once both agents are running, test the full flow:

```bash
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"
python test_integration.py
```

This will take 45-60 minutes and test:
- Design Agent job processing
- Tech Spec Agent triggering
- WebSocket communication
- TRD document generation

---

**Remember:** I can't get API keys or run system commands for you, but I've automated everything else! 🤖
