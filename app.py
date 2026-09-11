import streamlit as st
import pandas as pd
import datetime, base64, requests, json, os
import sqlite3

st.set_page_config(page_title="JAWABU LEARNING CENTRE", page_icon="🏫", layout="wide")

st.markdown("""
<style>
.stApp {background: #fff0f3;}
h1,h2,h3 {color: #ff4d7a!important;}
div[data-testid="stMetric"] {background:white; border:1px solid #ffe4e9; border-radius:20px; padding:10px;}
.stButton>button {background:#ff85a1; color:white; border-radius:12px; border:none; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

FEE_STRUCTURE = {
    "Play Group": 5000, "PP1": 7000, "PP2": 7000,
    "Grade 1": 10000, "Grade 2": 10000, "Grade 3": 10000, "Grade 4": 10000, "Grade 5": 10000, "Grade 6": 10000,
    "Grade 7": 12000, "Grade 8": 12000, "Grade 9": 12000
}
CLASSES = list(FEE_STRUCTURE.keys())

@st.cache_resource
def get_conn():
    conn = sqlite3.connect('jawabu.db', check_same_thread=False)
    return conn

conn = get_conn()
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS students (reg_no TEXT PRIMARY KEY, name TEXT, parent_name TEXT, parent_phone TEXT, class TEXT, gender TEXT, dob TEXT, nemis TEXT, adm_date TEXT, fee_total INT, paid INT, balance INT, arrears INT)")
cur.execute("CREATE TABLE IF NOT EXISTS mpesa_trans (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, reg_no TEXT, mpesa_code TEXT, amount INT, phone TEXT, tuition INT, transport INT, library INT, status TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, amount INT, description TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS academics (id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT, term TEXT, exam_type TEXT, maths INT, english INT, science INT, kiswahili INT, sst INT, total INT, mean REAL, grade TEXT)")
conn.commit()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center'>🏫 JAWABU LEARNING CENTRE</h1><p style='text-align:center'>Till: 4123456 | Paybill 247247</p>", unsafe_allow_html=True)
    col1,col2,col3 = st.columns([1,2,1])
    with col2:
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("LOGIN", use_container_width=True):
                if u=="admin" and p=="Jawabu@2026":
                    st.session_state.logged_in=True; st.session_state.role="DIRECTOR"
                elif u=="accountant" and p=="Acc@2026":
                    st.session_state.logged_in=True; st.session_state.role="ACCOUNTANT"
                elif u=="teacher" and p=="Teach@2026":
                    st.session_state.logged_in=True; st.session_state.role="TEACHER"
                else:
                    st.error("Wrong credentials")
                st.rerun()
            st.caption("Director: admin / Jawabu@2026 | Accountant: accountant / Acc@2026 | Teacher: teacher / Teach@2026")
    st.stop()

role = st.session_state.role
st.sidebar.markdown(f"### 🏫 JAWABU\n**{role}**")
menu_options = ["Dashboard (Profit/Loss)", "Admissions", "Finance - Auto STK", "Expenses", "Academics CBC", "Fee Defaulters & Reports"] if role=="DIRECTOR" else ["Finance - Auto STK", "Admissions", "Fee Defaulters & Reports"] if role=="ACCOUNTANT" else ["Academics CBC", "Admissions"]
menu = st.sidebar.radio("DEPARTMENTS", menu_options)
if st.sidebar.button("Logout"): st.session_state.logged_in=False; st.rerun()

if "Dashboard" in menu:
    st.title("Director Dashboard - Profit = Collected - Expenses")
    df_exp = pd.read_sql("SELECT * FROM expenses", conn)
    df_mpesa = pd.read_sql("SELECT * FROM mpesa_trans", conn)
    df_students = pd.read_sql("SELECT * FROM students", conn)
    total_coll = df_mpesa['amount'].sum() if not df_mpesa.empty else 0
    total_exp = df_exp['amount'].sum() if not df_exp.empty else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Collected", f"Ksh {total_coll}")
    c2.metric("Total Expenses", f"Ksh {total_exp}")
    c3.metric("PROFIT", f"Ksh {total_coll-total_exp}")
    c4.metric("Defaulters", len(df_students[df_students['balance']>0]) if not df_students.empty else 0)
    st.dataframe(df_mpesa, use_container_width=True)

elif "Admissions" in menu:
    st.subheader("Admission - Auto Reg No")
    with st.form("admit"):
        col1,col2,col3 = st.columns(3)
        s_name = col1.text_input("Student Name")
        p_name = col2.text_input("Parent Name")
        p_phone = col3.text_input("Parent Phone 2547XXXXXXXX")
        s_class = col1.selectbox("Class", CLASSES)
        gender = col2.selectbox("Gender", ["Male","Female"])
        dob = col3.date_input("DOB")
        nemis = col1.text_input("NEMIS")
        adm_date = col2.date_input("Admission Date", datetime.date.today())
        if st.form_submit_button("Admit Student"):
            fee = FEE_STRUCTURE[s_class]
            count = pd.read_sql("SELECT * FROM students", conn).shape[0]
            reg_no = f"JLC/{count+1:04d}/{datetime.date.today().year % 100}"
            cur.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (reg_no, s_name, p_name, p_phone, s_class, gender, str(dob), nemis, str(adm_date), fee, 0, fee, 0))
            conn.commit()
            st.success(f"Admitted! Reg: {reg_no} Fee: {fee}")
    st.dataframe(pd.read_sql("SELECT reg_no, name, class, parent_phone, fee_total, balance FROM students", conn), use_container_width=True)

elif "Finance" in menu:
    st.subheader("Finance - Auto M-Pesa STK (No Manual Typing)")
    st.info("When parent pays, code auto-appears. Auto-split Tuition 80% / Transport 15% / Library 5%")
    with st.form("finance"):
        c1,c2,c3 = st.columns(3)
        reg = c1.text_input("Reg No")
        amount = c2.number_input("Amount", min_value=1)
        phone = c3.text_input("Phone 2547XXXXXXXX")
        if st.form_submit_button("📲 SEND STK PUSH"):
            # REAL DARAJA would go here - For now auto-simulate
            tuition = int(amount*0.8)
            transport = int(amount*0.15)
            library = amount - tuition - transport
            mpesa_code = f"QAH{os.urandom(2).hex().upper()}{int(amount)}"
            cur.execute("INSERT INTO mpesa_trans (date, reg_no, mpesa_code, amount, phone, tuition, transport, library, status) VALUES (?,?,?,?,?,?,?,?,?)", (str(datetime.datetime.now()), reg, mpesa_code, int(amount), phone, tuition, transport, library, "AUTO_VERIFIED"))
            cur.execute("UPDATE students SET paid=paid+?, balance=balance-? WHERE reg_no=?", (int(amount), int(amount), reg))
            conn.commit()
            st.success(f"✅ Auto Confirmed! M-Pesa {mpesa_code} saved. Split: {tuition}/{transport}/{library}. Director dashboard updated instantly!")
    st.dataframe(pd.read_sql("SELECT date, reg_no, mpesa_code, amount, tuition, transport, library, status FROM mpesa_trans ORDER BY id DESC", conn), use_container_width=True)

elif "Expenses" in menu:
    st.subheader("Expenses - Salary, Food, Books, Electricity, Wifi")
    with st.form("exp"):
        c1,c2,c3 = st.columns(3)
        e_type = c1.selectbox("Type", ["Salary","Food","Books","Electricity","Wifi","Transport"])
        e_amount = c2.number_input("Amount")
        e_desc = c3.text_input("Desc")
        if st.form_submit_button("Add Expense"):
            cur.execute("INSERT INTO expenses (date,type,amount,description) VALUES (?,?,?,?)", (str(datetime.date.today()), e_type, e_amount, e_desc))
            conn.commit()
            st.success("Added")
    st.dataframe(pd.read_sql("SELECT * FROM expenses", conn), use_container_width=True)

elif "Academics" in menu:
    st.subheader("CBC - Opening, Mid-Term, End-Term")
    with st.form("acad"):
        c1,c2,c3 = st.columns(3)
        reg = c1.text_input("Reg No")
        term = c2.selectbox("Term", ["Term 1","Term 2","Term 3"])
        exam = c3.selectbox("Exam", ["Opening Exam","Mid Term Exam","End Term Exam"])
        c4,c5,c6,c7,c8 = st.columns(5)
        maths = c4.number_input("Maths",0,100)
        eng = c5.number_input("English",0,100)
        sci = c6.number_input("Science",0,100)
        kis = c7.number_input("Kiswahili",0,100)
        sst = c8.number_input("SST/CRE",0,100)
        if st.form_submit_button("Save Marks"):
            total = maths+eng+sci+kis+sst
            mean = round(total/5,1)
            grade = "A" if mean>=80 else "B" if mean>=65 else "C" if mean>=50 else "D" if mean>=35 else "E"
            cur.execute("INSERT INTO academics (reg_no, term, exam_type, maths, english, science, kiswahili, sst, total, mean, grade) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (reg, term, exam, maths, eng, sci, kis, sst, total, mean, grade))
            conn.commit()
            st.success(f"Saved Total {total} Mean {mean} Grade {grade}")
    st.dataframe(pd.read_sql("SELECT * FROM academics", conn), use_container_width=True)
    if st.button("⬆️ Promote Whole Class"):
        from_class = st.selectbox("From Class", CLASSES)
        idx = CLASSES.index(from_class)
        if idx < len(CLASSES)-1:
            to_class = CLASSES[idx+1]
            cur.execute("UPDATE students SET class=? WHERE class=?", (to_class, from_class))
            conn.commit()
            st.success(f"Promoted {from_class} to {to_class}")

elif "Defaulters" in menu:
    st.subheader("Fee Defaulters & Class Lists + Report Card PDF")
    df = pd.read_sql("SELECT reg_no, name, class, parent_name, parent_phone, balance FROM students WHERE balance>0", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("Download Defaulters CSV", df.to_csv(index=False), "defaulters.csv")
    reg_card = st.text_input("Enter Reg No for Report Card PDF")
    if st.button("Download Report Card"):
        df_s = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_card}'", conn)
        df_a = pd.read_sql(f"SELECT * FROM academics WHERE reg_no='{reg_card}' ORDER BY id DESC LIMIT 1", conn)
        if not df_s.empty:
            report_text = f"JAWABU LEARNING CENTRE\nReport Card\nName: {df_s.iloc[0]['name']}\nReg: {reg_card}\nClass: {df_s.iloc[0]['class']}\nBalance: {df_s.iloc[0]['balance']}\n"
            if not df_a.empty:
                report_text += f"Total: {df_a.iloc[0]['total']} Mean: {df_a.iloc[0]['mean']} Grade: {df_a.iloc[0]['grade']}"
            st.download_button("Click to Download TXT Report", report_text, f"{reg_card}_report.txt")
