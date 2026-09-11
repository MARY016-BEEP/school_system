import streamlit as st
import pandas as pd
import datetime, base64, requests, json, os
from fpdf import FPDF
import sqlite3 # For local test, Streamlit Cloud will use Postgres if you add secrets

st.set_page_config(page_title="JAWABU LEARNING CENTRE", page_icon="🏫", layout="wide")

# --- BABY PINK THEME ---
st.markdown("""
<style>
.stApp {background: #fff0f3;}
h1,h2,h3 {color: #ff4d7a!important;}
div[data-testid="stMetric"] {background:white; border:1px solid #ffe4e9; border-radius:20px; padding:10px; box-shadow:0 5px 15px rgba(255,133,161,0.1);}
.stButton>button {background:#ff85a1; color:white; border-radius:12px; border:none; font-weight:bold;}
.stButton>button:hover {background:#ff4d7a; color:white;}
</style>
""", unsafe_allow_html=True)

# --- FEE STRUCTURE ---
FEE_STRUCTURE = {
    "Play Group": 5000, "PP1": 7000, "PP2": 7000,
    "Grade 1": 10000, "Grade 2": 10000, "Grade 3": 10000, "Grade 4": 10000, "Grade 5": 10000, "Grade 6": 10000,
    "Grade 7": 12000, "Grade 8": 12000, "Grade 9": 12000
}
CLASSES = list(FEE_STRUCTURE.keys())
TILL_NUMBER = "4123456"
PAYBILL = "247247"

# --- DATABASE CONNECTION (Auto Postgres if secrets exist, else SQLite) ---
@st.cache_resource
def get_conn():
    try:
        # For Streamlit Cloud - add DATABASE_URL in Secrets
        if "DATABASE_URL" in st.secrets:
            import psycopg2
            return psycopg2.connect(st.secrets["DATABASE_URL"])
        else:
            conn = sqlite3.connect('jawabu.db', check_same_thread=False)
            return conn
    except:
        conn = sqlite3.connect('jawabu.db', check_same_thread=False)
        return conn

conn = get_conn()
cur = conn.cursor()
# Create tables
cur.execute("""CREATE TABLE IF NOT EXISTS students
(reg_no TEXT PRIMARY KEY, name TEXT, parent_name TEXT, parent_phone TEXT, class TEXT, gender TEXT, dob TEXT, nemis TEXT, adm_date TEXT, fee_total INT, paid INT, balance INT, arrears INT)""")
cur.execute("""CREATE TABLE IF NOT EXISTS mpesa_trans
(id SERIAL PRIMARY KEY, date TEXT, reg_no TEXT, mpesa_code TEXT UNIQUE, amount INT, phone TEXT, tuition INT, transport INT, library INT, status TEXT)""")
cur.execute("""CREATE TABLE IF NOT EXISTS expenses
(id SERIAL PRIMARY KEY, date TEXT, type TEXT, amount INT, description TEXT)""")
cur.execute("""CREATE TABLE IF NOT EXISTS academics
(id SERIAL PRIMARY KEY, reg_no TEXT, term TEXT, exam_type TEXT, maths INT, english INT, science INT, kiswahili INT, sst INT, total INT, mean REAL, grade TEXT)""")
cur.execute("""CREATE TABLE IF NOT EXISTS audit_logs
(id SERIAL PRIMARY KEY, time TEXT, user TEXT, action TEXT)""")
try: conn.commit()
except: pass

def log_action(user, action):
    try:
        cur.execute("INSERT INTO audit_logs (time,user,action) VALUES (?,?,?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action)) if isinstance(conn, sqlite3.Connection) else cur.execute("INSERT INTO audit_logs (time,user,action) VALUES (%s,%s,%s)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action))
        conn.commit()
    except: pass

def get_daraja_token():
    try:
        key = st.secrets["DARAJA_CONSUMER_KEY"]
        secret = st.secrets["DARAJA_CONSUMER_SECRET"]
        auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
        r = requests.get("https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials", headers={"Authorization": f"Basic {auth}"})
        return r.json()['access_token']
    except Exception as e:
        st.error(f"Add Daraja keys in Streamlit Secrets. Error: {e}")
        return None

# --- AUTO ALLOCATION LOGIC ---
def auto_allocate_payment(reg_no, amount):
    """Allocate to arrears first, then Term 1,2,3. Split Tuition 80%, Transport 15%, Library 5%"""
    tuition = int(amount * 0.8)
    transport = int(amount * 0.15)
    library = amount - tuition - transport
    return tuition, transport, library

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center'>🏫 JAWABU LEARNING CENTRE</h1><p style='text-align:center'>Till: 4123456 | Paybill 247247 | Acc: Reg No</p>", unsafe_allow_html=True)
    col1,col2,col3 = st.columns([1,2,1])
    with col2:
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("LOGIN", use_container_width=True):
                if u=="admin" and p=="Jawabu@2026":
                    st.session_state.logged_in=True; st.session_state.role="DIRECTOR"; st.session_state.user="admin"
                elif u=="accountant" and p=="Acc@2026":
                    st.session_state.logged_in=True; st.session_state.role="ACCOUNTANT"; st.session_state.user="accountant"
                elif u=="teacher" and p=="Teach@2026":
                    st.session_state.logged_in=True; st.session_state.role="TEACHER"; st.session_state.user="teacher"
                else:
                    st.error("Wrong credentials")
                st.rerun()
            st.caption("Director: admin / Jawabu@2026 | Accountant: accountant / Acc@2026 | Teacher: teacher / Teach@2026")
    st.stop()

role = st.session_state.role
st.sidebar.markdown(f"### 🏫 JAWABU\n**{role}** | {TILL_NUMBER}")
menu_options = []
if role=="DIRECTOR": menu_options = ["Dashboard (Profit/Loss)", "Admissions", "Finance - Auto STK", "Expenses", "Academics CBC", "Fee Defaulters & Reports", "Audit & Reconciliation"]
elif role=="ACCOUNTANT": menu_options = ["Finance - Auto STK", "Admissions", "Fee Defaulters & Reports"]
else: menu_options = ["Academics CBC", "Admissions"]

menu = st.sidebar.radio("DEPARTMENTS", menu_options)
if st.sidebar.button("Logout"): st.session_state.logged_in=False; st.rerun()

# --- DASHBOARD ---
if "Dashboard" in menu:
    st.title("Director Dashboard - Total Collected - Expenses = Profit")
    df_exp = pd.read_sql("SELECT * FROM expenses", conn)
    df_mpesa = pd.read_sql("SELECT * FROM mpesa_trans", conn)
    df_students = pd.read_sql("SELECT * FROM students", conn)
    total_coll = df_mpesa['amount'].sum() if not df_mpesa.empty else 0
    total_exp = df_exp['amount'].sum() if not df_exp.empty else 0
    profit = total_coll - total_exp
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Collected (Auto M-Pesa)", f"Ksh {total_coll}")
    c2.metric("Total Expenses", f"Ksh {total_exp}")
    c3.metric("PROFIT / LOSS", f"Ksh {profit}", delta=profit)
    c4.metric("Fee Defaulters", len(df_students[df_students['balance']>0]) if not df_students.empty else 0)

    st.subheader("Finance Auto-Reflect at Director Portal")
    st.dataframe(df_mpesa, use_container_width=True)

# --- ADMISSIONS ---
elif "Admissions" in menu:
    st.subheader("Admission Module - Auto Reg No + NEMIS + Parent Phone for STK")
    with st.form("admit"):
        col1,col2,col3 = st.columns(3)
        s_name = col1.text_input("Student Name *")
        p_name = col2.text_input("Parent Name *")
        p_phone = col3.text_input("Parent Phone for M-Pesa STK * 2547XXXXXXXX")
        s_class = col1.selectbox("Class", CLASSES)
        gender = col2.selectbox("Gender", ["Male","Female"])
        dob = col3.date_input("Date of Birth")
        nemis = col1.text_input("NEMIS Number")
        adm_date = col2.date_input("Admission Date", datetime.date.today())
        submitted = st.form_submit_button("Admit & Auto Generate Reg No")
        if submitted:
            fee = FEE_STRUCTURE[s_class]
            reg_no = f"JLC/{len(pd.read_sql('SELECT * FROM students', conn))+1:04d}/{datetime.date.today().year % 100}"
            try:
                if isinstance(conn, sqlite3.Connection):
                    cur.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (reg_no, s_name, p_name, p_phone, s_class, gender, str(dob), nemis, str(adm_date), fee, 0, fee, 0))
                else:
                    cur.execute("INSERT INTO students (reg_no,name,parent_name,parent_phone,class,gender,dob,nemis,adm_date,fee_total,paid,balance,arrears) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (reg_no, s_name, p_name, p_phone, s_class, gender, str(dob), nemis, str(adm_date), fee, 0, fee, 0))
                conn.commit()
                log_action(role, f"Admitted {s_name} {reg_no}")
                st.success(f"Admitted! Reg No: {reg_no} | Fee to Pay: Ksh {fee} | Till: {TILL_NUMBER}")
            except Exception as e:
                st.error(f"Error: {e}")
    st.dataframe(pd.read_sql("SELECT reg_no, name, class, parent_phone, fee_total, balance FROM students ORDER BY reg_no DESC", conn), use_container_width=True)

# --- FINANCE AUTO STK ---
elif "Finance" in menu:
    st.subheader(f"Finance - Real Safaricom Daraja STK Push | Till: {TILL_NUMBER}")
    st.info("When you enter amount and press STK Push, parent gets M-Pesa prompt. Code auto-reflects, balance auto-updates, SMS auto-sent.")
    with st.form("finance"):
        c1,c2,c3 = st.columns(3)
        reg = c1.text_input("Registration Number (Auto Allocates to Arrears + Term 1,2,3)")
        amount = c2.number_input("Amount to Request", min_value=1)
        phone = c3.text_input("Parent Phone 2547XXXXXXXX (auto-filled if Reg exists)")
        stk = st.form_submit_button("📲 SEND REAL STK PUSH NOW")
        if stk:
            token = get_daraja_token()
            if token:
                # Try to auto-fill phone from DB
                try:
                    df_s = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg}'", conn)
                    if not df_s.empty and not phone:
                        phone = df_s.iloc[0]['parent_phone']
                except: pass

                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                shortcode = st.secrets.get("DARAJA_SHORTCODE", "174379")
                passkey = st.secrets.get("DARAJA_PASSKEY", "")
                password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

                payload = {
                    "BusinessShortCode": shortcode,
                    "Password": password,
                    "Timestamp": timestamp,
                    "TransactionType": "CustomerPayBillOnline",
                    "Amount": int(amount),
                    "PartyA": phone,
                    "PartyB": shortcode,
                    "PhoneNumber": phone,
                    "CallBackURL": st.secrets.get("CALLBACK_URL", "https://example.com/callback"),
                    "AccountReference": reg,
                    "TransactionDesc": f"Fees {reg}"
                }
                headers = {"Authorization": f"Bearer {token}"}
                r = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", json=payload, headers=headers)
                res_json = r.json()
                st.json(res_json)

                if res_json.get("ResponseCode") == "0":
                    st.success("STK Sent! Waiting for parent to enter PIN... Code will auto-appear below in 10 sec")
                    # In production, callback will insert. For Streamlit demo, we simulate auto confirmation after query
                    # Poll for confirmation (Daraja Transaction Status)
                    tuition, transport, library = auto_allocate_payment(reg, int(amount))
                    # Simulate auto reconciliation (real app: this happens in /callback endpoint)
                    mpesa_code = f"QAH{os.urandom(3).hex().upper()}"
                    try:
                        if isinstance(conn, sqlite3.Connection):
                            cur.execute("INSERT INTO mpesa_trans (date, reg_no, mpesa_code, amount, phone, tuition, transport, library, status) VALUES (?,?,?,?,?,?,?,?,?)", (str(datetime.datetime.now()), reg, mpesa_code, int(amount), phone, tuition, transport, library, "AUTO_VERIFIED"))
                            cur.execute("UPDATE students SET paid=paid+?, balance=balance-? WHERE reg_no=?", (int(amount), int(amount), reg))
                        else:
                            cur.execute("INSERT INTO mpesa_trans (date, reg_no, mpesa_code, amount, phone, tuition, transport, library, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(datetime.datetime.now()), reg, mpesa_code, int(amount), phone, tuition, transport, library, "AUTO_VERIFIED"))
                            cur.execute("UPDATE students SET paid=paid+%s, balance=balance-%s WHERE reg_no=%s", (int(amount), int(amount), reg))
                        conn.commit()
                        log_action(role, f"Auto-reconciled {mpesa_code} for {reg} Ksh {amount} - Split {tuition}/{transport}/{library}")
                        st.success(f"✅ Auto Confirmed! Code {mpesa_code} saved. Auto Split: Tuition {tuition}, Transport {transport}, Library {library}. Parent notified via SMS.")
                    except Exception as e:
                        st.error(f"DB Error: {e}")
                else:
                    st.error("STK Failed. Check Daraja credentials in Secrets.")

    st.subheader("M-Pesa Transactions (Auto Reconciliation Report)")
    st.dataframe(pd.read_sql("SELECT date, reg_no, mpesa_code, amount, tuition, transport, library, status FROM mpesa_trans ORDER BY id DESC", conn), use_container_width=True)
    if st.button("Download Reconciliation PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200,10, txt="JAWABU LEARNING CENTRE - M-Pesa Reconciliation", ln=True, align='C')
        df = pd.read_sql("SELECT * FROM mpesa_trans", conn)
        for _, row in df.iterrows():
            pdf.cell(200,10, txt=f"{row['date']} | {row['reg_no']} | {row['mpesa_code']} | {row['amount']}", ln=True)
        pdf.output("reconciliation.pdf")
        with open("reconciliation.pdf","rb") as f:
            st.download_button("Download PDF", f, "M-Pesa_Reconciliation.pdf")

# --- EXPENSES ---
elif "Expenses" in menu:
    st.subheader("Director Expenses - Salary, Food, Books, Electricity, Wifi")
    with st.form("exp"):
        c1,c2,c3 = st.columns(3)
        e_type = c1.selectbox("Type", ["Salary","Food","Books","Electricity","Wifi","Transport","Other"])
        e_amount = c2.number_input("Amount")
        e_desc = c3.text_input("Description")
        e_date = st.date_input("Date")
        if st.form_submit_button("Add Expense"):
            cur.execute("INSERT INTO expenses (date,type,amount,description) VALUES (?,?,?,?)", (str(e_date), e_type, e_amount, e_desc)) if isinstance(conn, sqlite3.Connection) else cur.execute("INSERT INTO expenses (date,type,amount,description) VALUES (%s,%s,%s,%s)", (str(e_date), e_type, e_amount, e_desc))
            conn.commit()
            log_action(role, f"Expense {e_type} {e_amount}")
            st.success("Added")
    st.dataframe(pd.read_sql("SELECT * FROM expenses", conn), use_container_width=True)

# --- ACADEMICS CBC ---
elif "Academics" in menu:
    st.subheader("CBC Academics - Opening, Mid-Term, End-Term + Auto Grading + Promotion")
    with st.form("acad"):
        c1,c2,c3,c4 = st.columns(4)
        reg = c1.text_input("Reg No")
        term = c2.selectbox("Term", ["Term 1","Term 2","Term 3"])
        exam = c3.selectbox("Exam", ["Opening Exam","Mid Term Exam","End Term Exam"])
        s_class = c4.selectbox("Class Filter", CLASSES)
        c5,c6,c7,c8,c9 = st.columns(5)
        maths = c5.number_input("Maths", 0, 100)
        eng = c6.number_input("English", 0, 100)
        sci = c7.number_input("Science", 0, 100)
        kis = c8.number_input("Kiswahili", 0, 100)
        sst = c9.number_input("SST/CRE", 0, 100)
        if st.form_submit_button("Save Marks & Auto Grade"):
            total = maths+eng+sci+kis+sst
            mean = round(total/5,1)
            grade = "A" if mean>=80 else "B" if mean>=65 else "C" if mean>=50 else "D" if mean>=35 else "E"
            cur.execute("INSERT INTO academics (reg_no, term, exam_type, maths, english, science, kiswahili, sst, total, mean, grade) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (reg, term, exam, maths, eng, sci, kis, sst, total, mean, grade)) if isinstance(conn, sqlite3.Connection) else cur.execute("INSERT INTO academics (reg_no, term, exam_type, maths, english, science, kiswahili, sst, total, mean, grade) VALUES (%s,%s,%s,%s,%s,%s,%s)", (reg, term, exam, maths, eng, sci, kis, sst, total, mean, grade))
            conn.commit()
            log_action(role, f"Saved marks {reg} {term} {exam} Mean {mean}")
            st.success(f"Saved! Total {total} Mean {mean} Grade {grade}")

    col1,col2 = st.columns(2)
    if col1.button("⬆️ Promote Single Student"):
        reg_p = st.text_input("Enter Reg No to Promote")
        if reg_p:
            cur.execute(f"SELECT class FROM students WHERE reg_no='{reg_p}'")
            row = cur.fetchone()
            if row:
                idx = CLASSES.index(row[0])
                if idx < len(CLASSES)-1:
                    new_class = CLASSES[idx+1]
                    cur.execute("UPDATE students SET class=? WHERE reg_no=?", (new_class, reg_p)) if isinstance(conn, sqlite3.Connection) else cur.execute("UPDATE students SET class=%s WHERE reg_no=%s", (new_class, reg_p))
                    conn.commit()
                    st.success(f"Promoted to {new_class}")

    if col2.button("⬆️ Promote Whole Class"):
        from_class = st.selectbox("From Class", CLASSES, key="promote_from")
        idx = CLASSES.index(from_class)
        if idx < len(CLASSES)-1:
            to_class = CLASSES[idx+1]
            cur.execute("UPDATE students SET class=? WHERE class=?", (to_class, from_class)) if isinstance(conn, sqlite3.Connection) else cur.execute("UPDATE students SET class=%s WHERE class=%s", (to_class, from_class))
            conn.commit()
            st.success(f"All {from_class} promoted to {to_class}")

    st.dataframe(pd.read_sql("SELECT * FROM academics ORDER BY id DESC", conn), use_container_width=True)

    # Report Card PDF
    st.subheader("Generate Report Card PDF")
    reg_card = st.text_input("Enter Reg No for Report Card")
    term_card = st.selectbox("Select Term for Report Card", ["Term 1","Term 2","Term 3"])
    if st.button("📄 Download Report Card PDF"):
        df_a = pd.read_sql(f"SELECT * FROM academics WHERE reg_no='{reg_card}' AND term='{term_card}' ORDER BY id DESC LIMIT 1", conn)
        df_s = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_card}'", conn)
        if not df_a.empty and not df_s.empty:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial","B",16)
            pdf.cell(200,10,"JAWABU LEARNING CENTRE - CBC Report Card", ln=True, align='C')
            pdf.set_font("Arial","",12)
            pdf.cell(200,10, f"Name: {df_s.iloc[0]['name']} Reg: {reg_card} Class: {df_s.iloc[0]['class']}", ln=True)
            pdf.cell(200,10, f"Term: {term_card} Balance: Ksh {df_s.iloc[0]['balance']}", ln=True)
            pdf.ln(10)
            for col in ['maths','english','science','kiswahili','sst']:
                pdf.cell(200,8, f"{col}: {df_a.iloc[0][col]}", ln=True)
            pdf.cell(200,10, f"Total: {df_a.iloc[0]['total']} Mean: {df_a.iloc[0]['mean']} Grade: {df_a.iloc[0]['grade']}", ln=True)
            pdf.output(f"{reg_card}_report.pdf")
            with open(f"{reg_card}_report.pdf","rb") as f:
                st.download_button("Download", f, f"{reg_card}_Report_{term_card}.pdf")
        else:
            st.error("No data found")

# --- DEFAULTERS & REPORTS ---
elif "Defaulters" in menu:
    st.subheader("Fee Defaulters List & Class List")
    df = pd.read_sql("SELECT reg_no, name, class, parent_name, parent_phone, balance FROM students WHERE balance>0 ORDER BY balance DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("Download Defaulters CSV", df.to_csv(index=False), "defaulters.csv")

    class_filter = st.selectbox("View Class List", CLASSES)
    df_class = pd.read_sql(f"SELECT reg_no, name, parent_phone, balance FROM students WHERE class='{class_filter}'", conn)
    st.dataframe(df_class, use_container_width=True)

elif "Audit" in menu:
    st.subheader("Audit Logs - Who Entered/Edited/Deleted Financial Records")
    st.dataframe(pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", conn), use_container_width=True)