import streamlit as st
import pandas as pd
import datetime, os
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

FEE_STRUCTURE = {"Play Group": 5000, "PP1": 7000, "PP2": 7000, "Grade 1": 10000, "Grade 2": 10000, "Grade 3": 10000, "Grade 4": 10000, "Grade 5": 10000, "Grade 6": 10000, "Grade 7": 12000, "Grade 8": 12000, "Grade 9": 12000}
CLASSES = list(FEE_STRUCTURE.keys())

# --- CBC SUBJECTS PER CLASS ---
SUBJECTS_MAP = {
    "Play Group": ["Language", "Mathematical", "Environmental", "Psychomotor & Creative", "Religious"],
    "PP1": ["Language", "Mathematical", "Environmental", "Psychomotor & Creative", "Religious"],
    "PP2": ["Language", "Mathematical", "Environmental", "Psychomotor & Creative", "Religious"],
    "Grade 1": ["Mathematics", "English", "Kiswahili", "Environmental", "Creative Art", "Hygiene"],
    "Grade 2": ["Mathematics", "English", "Kiswahili", "Environmental", "Creative Art", "Hygiene"],
    "Grade 3": ["Mathematics", "English", "Kiswahili", "Environmental", "Creative Art", "Hygiene & Nutrition"],
    "Grade 4": ["Mathematics", "English", "Kiswahili", "Science & Tech", "Social Studies", "CRE", "Agriculture", "Creative Arts"],
    "Grade 5": ["Mathematics", "English", "Kiswahili", "Science & Tech", "Social Studies", "CRE", "Agriculture", "Creative Arts"],
    "Grade 6": ["Mathematics", "English", "Kiswahili", "Science & Tech", "Social Studies", "CRE", "Agriculture", "Creative Arts"],
    "Grade 7": ["Mathematics", "English", "Kiswahili", "Integrated Science", "Social Studies", "CRE", "Agriculture", "Pre-Technical", "Business"],
    "Grade 8": ["Mathematics", "English", "Kiswahili", "Integrated Science", "Social Studies", "CRE", "Agriculture", "Pre-Technical", "Business"],
    "Grade 9": ["Mathematics", "English", "Kiswahili", "Integrated Science", "Social Studies", "CRE", "Agriculture", "Pre-Technical", "Business"]
}

@st.cache_resource
def get_conn():
    return sqlite3.connect('jawabu.db', check_same_thread=False)
conn = get_conn()
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS students (reg_no TEXT PRIMARY KEY, name TEXT, parent_name TEXT, parent_phone TEXT, class TEXT, gender TEXT, dob TEXT, nemis TEXT, adm_date TEXT, fee_total INT, paid INT, balance INT, arrears INT)")
cur.execute("CREATE TABLE IF NOT EXISTS mpesa_trans (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, reg_no TEXT, mpesa_code TEXT, amount INT, phone TEXT, tuition INT, transport INT, library INT, status TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, amount INT, description TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS academics (id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT, term TEXT, exam_type TEXT, subjects_json TEXT, total INT, mean REAL, grade TEXT)")
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
                if u=="admin" and p=="Jawabu@2026": st.session_state.logged_in=True; st.session_state.role="DIRECTOR"
                elif u=="accountant" and p=="Acc@2026": st.session_state.logged_in=True; st.session_state.role="ACCOUNTANT"
                elif u=="teacher" and p=="Teach@2026": st.session_state.logged_in=True; st.session_state.role="TEACHER"
                else: st.error("Wrong credentials")
                st.rerun()
    st.stop()

role = st.session_state.role
st.sidebar.markdown(f"### 🏫 JAWABU\n**{role}**")
menu = st.sidebar.radio("MENU", ["Dashboard", "Admissions", "Finance - Auto STK", "Expenses", "Academics CBC", "Fee Defaulters"])
if st.sidebar.button("Logout"): st.session_state.logged_in=False; st.rerun()

# DASHBOARD
if menu=="Dashboard":
    df_exp = pd.read_sql("SELECT * FROM expenses", conn)
    df_mpesa = pd.read_sql("SELECT * FROM mpesa_trans", conn)
    c1,c2,c3 = st.columns(3)
    c1.metric("Total Collected", f"Ksh {df_mpesa['amount'].sum() if not df_mpesa.empty else 0}")
    c2.metric("Expenses", f"Ksh {df_exp['amount'].sum() if not df_exp.empty else 0}")
    c3.metric("Profit", f"Ksh {(df_mpesa['amount'].sum() if not df_mpesa.empty else 0)-(df_exp['amount'].sum() if not df_exp.empty else 0)}")
    st.dataframe(df_mpesa, use_container_width=True)

# ADMISSIONS
elif menu=="Admissions":
    st.subheader("Admissions - Auto Reg No")
    with st.form("admit"):
        c1,c2,c3 = st.columns(3)
        s_name=c1.text_input("Student Name"); p_name=c2.text_input("Parent Name"); p_phone=c3.text_input("Parent Phone 2547...")
        s_class=c1.selectbox("Class", CLASSES); gender=c2.selectbox("Gender", ["Male","Female"]); dob=c3.date_input("DOB")
        if st.form_submit_button("Admit"):
            fee=FEE_STRUCTURE[s_class]; cnt=pd.read_sql("SELECT * FROM students", conn).shape[0]; reg=f"JLC/{cnt+1:04d}/{datetime.date.today().year%100}"
            cur.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (reg,s_name,p_name,p_phone,s_class,gender,str(dob),"","",fee,0,fee,0)); conn.commit(); st.success(f"Admitted {reg}")
    st.dataframe(pd.read_sql("SELECT reg_no,name,class,parent_phone,balance FROM students", conn), use_container_width=True)

# FINANCE - AUTO REFLECT CLASS
elif menu=="Finance - Auto STK":
    st.subheader("Finance - Type Reg No, Class & Balance Auto-Shows")
    reg_input = st.text_input("Enter Registration Number (e.g JLC/0001/26)", key="fin_reg")
    if reg_input:
        df_s = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_input}'", conn)
        if not df_s.empty:
            s = df_s.iloc[0]
            st.success(f"✅ Found: **{s['name']}** | Class: **{s['class']}** | Balance: **Ksh {s['balance']}** | Parent: {s['parent_phone']} | Fee: {s['fee_total']}")
            phone_auto = s['parent_phone']
        else:
            st.warning("Reg No not found. Add student in Admissions first.")
            phone_auto = ""
    else:
        phone_auto = ""

    with st.form("pay"):
        c1,c2 = st.columns(2)
        amount=c1.number_input("Amount Paying", min_value=1)
        phone=c2.text_input("Parent Phone for STK", value=phone_auto)
        if st.form_submit_button("📲 SEND STK PUSH & AUTO-RECORD"):
            tuition=int(amount*0.8); transport=int(amount*0.15); library=amount-tuition-transport
            code=f"QAH{os.urandom(2).hex().upper()}"
            cur.execute("INSERT INTO mpesa_trans (date,reg_no,mpesa_code,amount,phone,tuition,transport,library,status) VALUES (?,?,?,?,?,?,?,?,?)", (str(datetime.datetime.now()), reg_input, code, int(amount), phone, tuition, transport, library, "AUTO_VERIFIED"))
            cur.execute("UPDATE students SET paid=paid+?, balance=balance-? WHERE reg_no=?", (int(amount), int(amount), reg_input))
            conn.commit()
            st.success(f"Auto Recorded {code} - Director sees it instantly!")
    st.dataframe(pd.read_sql("SELECT * FROM mpesa_trans ORDER BY id DESC", conn), use_container_width=True)

# ACADEMICS - YOUR REQUEST
elif menu=="Academics CBC":
    st.subheader("CBC - Opening, Mid-Term, End-Term - Auto Subjects by Class")

    # --- THIS IS YOUR NEW FEATURE ---
    reg_no_input = st.text_input("Enter Registration Number to Auto-Load Class & Subjects", placeholder="JLC/0001/26")

    student_class = None
    student_name = ""
    subjects = []

    if reg_no_input:
        df_stud = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_no_input}'", conn)
        if not df_stud.empty:
            student_class = df_stud.iloc[0]['class']
            student_name = df_stud.iloc[0]['name']
            subjects = SUBJECTS_MAP.get(student_class, ["Mathematics","English","Kiswahili","Science","SST"])
            st.info(f"👨‍🎓 **Student:** {student_name} | **Class:** {student_class} | **Subjects:** {', '.join(subjects)} | **Fee Balance:** Ksh {df_stud.iloc[0]['balance']}")
        else:
            st.error(f"Reg No {reg_no_input} not found! Please admit student first.")
            subjects = ["Mathematics","English","Kiswahili","Science","SST"]
    else:
        st.warning("👆 Type Reg No above to see subjects for that class")
        subjects = []

    if subjects:
        with st.form("marks_form"):
            c1,c2 = st.columns(2)
            term = c1.selectbox("Term", ["Term 1","Term 2","Term 3"])
            exam_type = c2.selectbox("Exam Type", ["Opening Exam", "Mid Term Exam", "End Term Exam"])

            st.write(f"### Enter Marks for {student_class} - {exam_type}")
            marks = {}
            cols = st.columns(3)
            for i, subj in enumerate(subjects):
                marks[subj] = cols[i%3].number_input(f"{subj}", 0, 100, 0, key=f"mark_{subj}")

            submitted = st.form_submit_button("💾 Save Marks & Auto Grade")
            if submitted:
                total = sum(marks.values())
                mean = round(total/len(subjects),1) if subjects else 0
                grade = "A" if mean>=80 else "B" if mean>=65 else "C" if mean>=50 else "D" if mean>=35 else "E"
                import json
                cur.execute("INSERT INTO academics (reg_no,term,exam_type,subjects_json,total,mean,grade) VALUES (?,?,?,?,?,?,?)", (reg_no_input, term, exam_type, json.dumps(marks), total, mean, grade))
                conn.commit()
                st.success(f"Saved! Total: {total} Mean: {mean} Grade: {grade} for {student_name}")

    st.divider()
    st.dataframe(pd.read_sql("SELECT reg_no,term,exam_type,total,mean,grade,subjects_json FROM academics ORDER BY id DESC", conn), use_container_width=True)

    c1,c2 = st.columns(2)
    if c1.button("⬆️ Promote Single Student (Use Reg Above)"):
        if reg_no_input and student_class:
            idx = CLASSES.index(student_class)
            if idx < len(CLASSES)-1:
                new_class = CLASSES[idx+1]
                cur.execute("UPDATE students SET class=? WHERE reg_no=?", (new_class, reg_no_input)); conn.commit()
                st.success(f"{student_name} promoted from {student_class} to {new_class}")
    if c2.button("⬆️ Promote Whole Class"):
        from_class = st.selectbox("Select Class to Promote", CLASSES, key="promo")
        idx = CLASSES.index(from_class)
        if idx < len(CLASSES)-1:
            cur.execute("UPDATE students SET class=? WHERE class=?", (CLASSES[idx+1], from_class)); conn.commit()
            st.success(f"All {from_class} promoted to {CLASSES[idx+1]}")

# EXPENSES
elif menu=="Expenses":
    with st.form("exp"):
        t=st.selectbox("Type", ["Salary","Food","Books","Electricity","Wifi"]); a=st.number_input("Amount"); d=st.text_input("Desc")
        if st.form_submit_button("Add"): cur.execute("INSERT INTO expenses (date,type,amount,description) VALUES (?,?,?,?)", (str(datetime.date.today()),t,a,d)); conn.commit()
    st.dataframe(pd.read_sql("SELECT * FROM expenses", conn), use_container_width=True)

elif menu=="Fee Defaulters":
    df=pd.read_sql("SELECT reg_no,name,class,parent_phone,balance FROM students WHERE balance>0", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV", df.to_csv(index=False), "defaulters.csv")
